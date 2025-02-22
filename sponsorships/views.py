from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db import transaction
from django.contrib import messages
from django.utils import timezone
import logging
import json
from .models import Sponsorship, SponsorshipCategory, SponsorshipPayment
from .services import FlutterwaveService
from django.urls import reverse
from django.db.models import Sum, Count

logger = logging.getLogger(__name__)

def sponsorship_list(request):
    categories = SponsorshipCategory.objects.all()
    category_slug = request.GET.get('category')
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', '-created_at')
    
    sponsorships = Sponsorship.objects.filter(status='active')
    
    # Apply category filter
    if category_slug:
        category = get_object_or_404(SponsorshipCategory, slug=category_slug)
        sponsorships = sponsorships.filter(category=category)
    
    # Apply search filter
    if search_query:
        sponsorships = sponsorships.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Apply sorting
    valid_sort_fields = {
        'newest': '-created_at',
        'oldest': 'created_at',
        'most-sponsors': '-total_sponsors',
        'least-sponsors': 'total_sponsors',
        'amount-high': '-monthly_amount',
        'amount-low': 'monthly_amount',
    }
    sort_field = valid_sort_fields.get(sort_by, '-created_at')
    sponsorships = sponsorships.order_by(sort_field)
    
    # Calculate statistics
    total_sponsorships = sponsorships.count()
    total_sponsors = SponsorshipPayment.objects.filter(
        status='success'
    ).values('sponsor').distinct().count()
    total_amount_raised = SponsorshipPayment.objects.filter(
        status='success'
    ).aggregate(total=Sum('amount'))['total'] or 0
    
    paginator = Paginator(sponsorships, 9)
    page = request.GET.get('page')
    sponsorships = paginator.get_page(page)
    
    context = {
        'sponsorships': sponsorships,
        'categories': categories,
        'current_category': category_slug,
        'search_query': search_query,
        'sort_by': sort_by,
        'total_sponsorships': total_sponsorships,
        'total_sponsors': total_sponsors,
        'total_amount_raised': total_amount_raised,
    }
    return render(request, 'sponsorships/sponsorship_list.html', context)

def sponsorship_detail(request, slug):
    sponsorship = get_object_or_404(Sponsorship, slug=slug, status='active')
    recent_sponsors = SponsorshipPayment.objects.filter(
        sponsorship=sponsorship,
        status='success'
    ).select_related('sponsor').order_by('-payment_date')[:5]
    
    context = {
        'sponsorship': sponsorship,
        'recent_sponsors': recent_sponsors
    }
    return render(request, 'sponsorships/sponsorship_detail.html', context)

@login_required
@require_POST
def process_sponsorship(request, sponsorship_id):
    try:
        sponsorship = Sponsorship.objects.get(id=sponsorship_id)
        data = json.loads(request.body)
        
        months = int(data.get('months', 1))
        amount = float(sponsorship.monthly_amount * months)
        
        if amount < 1:
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid sponsorship amount'
            }, status=400)
        
        flw_service = FlutterwaveService()
        payment_response = flw_service.initialize_payment(
            user=request.user,
            amount=amount,
            email=request.user.email,
            tx_ref=f"spn-{sponsorship.id}-{timezone.now().timestamp()}",
            callback_url=request.build_absolute_uri(reverse('sponsorships:verify-payment'))
        )
        
        if payment_response['status'] == 'success':
            payment = SponsorshipPayment.objects.create(
                sponsorship=sponsorship,
                sponsor=request.user,
                amount=amount,
                months=months,
                transaction_reference=payment_response['tx_ref'],
                is_anonymous=data.get('is_anonymous', False),
                is_recurring=data.get('is_recurring', False)
            )
            
            return JsonResponse({
                'status': 'success',
                'payment_link': payment_response['data']['link']
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': payment_response.get('message', 'Payment initialization failed')
            }, status=400)
            
    except Exception as e:
        logger.error(f"Sponsorship payment error: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

@login_required
def verify_payment(request):
    """
    Handle Flutterwave payment verification callback
    """
    tx_ref = request.GET.get('tx_ref')
    transaction_id = request.GET.get('transaction_id')
    status = request.GET.get('status')

    logger.info(f"Payment verification callback received: tx_ref={tx_ref}, status={status}")

    try:
        # Get the pending payment
        payment = get_object_or_404(
            SponsorshipPayment, 
            transaction_reference=tx_ref,
            status='pending'
        )

        if status == 'successful':
            # Verify with Flutterwave
            flw_service = FlutterwaveService()
            verification = flw_service.verify_payment(transaction_id)

            if verification.get('status') == 'success':
                # Update payment status
                with transaction.atomic():
                    payment.status = 'success'
                    payment.save()

                    # Update sponsorship stats
                    sponsorship = payment.sponsorship
                    sponsorship.total_sponsors = SponsorshipPayment.objects.filter(
                        sponsorship=sponsorship,
                        status='success'
                    ).count()
                    sponsorship.save()

                messages.success(
                    request, 
                    'Thank you! Your sponsorship payment was successful.'
                )
                return redirect(
                    'sponsorships:sponsorship-detail', 
                    slug=payment.sponsorship.slug
                )

        # Handle failed payment
        payment.status = 'failed'
        payment.save()
        messages.error(
            request, 
            'Payment verification failed. Please try again.'
        )
        return redirect(
            'sponsorships:sponsorship-detail', 
            slug=payment.sponsorship.slug
        )

    except Exception as e:
        logger.error(f"Payment verification error: {str(e)}")
        messages.error(
            request, 
            'An error occurred while verifying your payment.'
        )
        return redirect('sponsorships:sponsorship-list')
