from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
from django.contrib import messages
from django.conf import settings
import json
import logging
from .models import Campaign, CampaignCategory, Donation
from .utils import initialize_flutterwave_payment, verify_flutterwave_payment
from .services import FlutterwaveService

logger = logging.getLogger(__name__)

def campaign_list(request):
    categories = CampaignCategory.objects.all()
    category_slug = request.GET.get('category')
    search_query = request.GET.get('search', '')
    sort_by = request.GET.get('sort', '-created_at')
    
    campaigns = Campaign.objects.filter(is_active=True)
    
    # Apply category filter
    if category_slug:
        category = get_object_or_404(CampaignCategory, slug=category_slug)
        campaigns = campaigns.filter(category=category)
    
    # Apply search filter
    if search_query:
        campaigns = campaigns.filter(title__icontains=search_query)
    
    # Apply sorting
    valid_sort_fields = {
        'newest': '-created_at',
        'oldest': 'created_at',
        'most-funded': '-raised_amount',
        'least-funded': 'raised_amount',
        'closing-soon': 'end_date',
    }
    sort_field = valid_sort_fields.get(sort_by, '-created_at')
    campaigns = campaigns.order_by(sort_field)

    # Pagination
    paginator = Paginator(campaigns, 9)
    page = request.GET.get('page')
    campaigns = paginator.get_page(page)

    context = {
        'campaigns': campaigns,
        'categories': categories,
        'current_category': category_slug,
        'search_query': search_query,
        'sort_by': sort_by,
        'total_campaigns': campaigns.paginator.count
    }
    return render(request, 'campaigns/campaign_list.html', context)

def campaign_detail(request, slug):
    campaign = get_object_or_404(Campaign, slug=slug, is_active=True)
    related_campaigns = Campaign.objects.filter(
        category=campaign.category, 
        is_active=True
    ).exclude(id=campaign.id)[:3]
    
    # Get donations only if they exist
    try:
        donations = campaign.donation_set.filter(status='success').order_by('-created_at')
    except AttributeError:
        donations = []
    
    context = {
        'campaign': campaign,
        'related_campaigns': related_campaigns,
        'donations': donations,
    }
    return render(request, 'campaigns/campaign_detail.html', context)

@login_required
@require_POST
def process_donation(request, campaign_id):
    try:
        campaign = Campaign.objects.get(id=campaign_id)
        data = json.loads(request.body)
        amount = float(data.get('amount', 0))
        
        if amount < 1:
            return JsonResponse({
                'status': 'error',
                'message': 'Minimum donation amount is ₦1'
            }, status=400)

        # Initialize payment
        flw_service = FlutterwaveService()
        payment_response = flw_service.initialize_payment(
            user=request.user,
            campaign=campaign,
            amount=amount,
            is_anonymous=data.get('is_anonymous', False)
        )
        
        if payment_response['status'] == 'success':
            # Create pending donation record
            donation = Donation.objects.create(
                campaign=campaign,
                donor=request.user,
                amount=amount,
                transaction_reference=payment_response['tx_ref'],
                status='pending',
                is_anonymous=data.get('is_anonymous', False)
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
            
    except Campaign.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Campaign not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Payment error: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)

@csrf_exempt
def flutterwave_webhook(request):
    """Handle webhook notifications from Flutterwave"""
    if request.method != 'POST':
        return HttpResponse(status=405)
    
    # Verify webhook signature
    signature = request.headers.get('verif-hash')
    if not signature or signature != settings.FLUTTERWAVE_WEBHOOK_HASH:
        return HttpResponse(status=401)
    
    try:
        # Parse webhook data
        data = json.loads(request.body)
        if data['status'] == 'successful':
            tx_ref = data['txRef']
            
            with transaction.atomic():
                # Get and update donation
                donation = Donation.objects.select_related('campaign').get(
                    transaction_reference=tx_ref,
                    status='pending'
                )
                
                # Update donation status
                donation.status = 'success'
                donation.save()
                
                # Update campaign raised amount
                campaign = donation.campaign
                campaign.raised_amount += donation.amount
                campaign.save()
                
        return HttpResponse(status=200)
        
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        return HttpResponse(str(e), status=400)

@require_GET
def verify_payment(request):
    """Handle payment verification callback from Flutterwave"""
    status = request.GET.get('status')
    tx_ref = request.GET.get('tx_ref')
    transaction_id = request.GET.get('transaction_id')
    
    logger.info(f"Payment callback: status={status}, tx_ref={tx_ref}, transaction_id={transaction_id}")
    
    try:
        donation = Donation.objects.select_related('campaign').get(transaction_reference=tx_ref)
        
        if status == 'successful':
            # Verify with Flutterwave
            verification = verify_flutterwave_payment(transaction_id)
            
            if verification['status'] == 'success':
                with transaction.atomic():
                    donation.status = 'success'
                    donation.save()
                    
                    # Update campaign raised amount
                    campaign = donation.campaign
                    campaign.raised_amount += donation.amount
                    campaign.save()
                    
                    messages.success(
                        request, 
                        'Thank you for your donation! Your payment has been processed successfully.'
                    )
            else:
                donation.status = 'failed'
                donation.save()
                messages.error(
                    request, 
                    'Payment verification failed. Please contact support if you believe this is an error.'
                )
        else:
            donation.status = 'failed'
            donation.save()
            messages.warning(request, 'Payment was cancelled or unsuccessful.')
        
        return redirect('campaigns:campaign-detail', slug=donation.campaign.slug)
        
    except Donation.DoesNotExist:
        messages.error(
            request, 
            'Could not find the associated donation. Please contact support.'
        )
        return redirect('home')

def home(request):
    # ... your existing context ...
    context = {
        'all_campaigns': Campaign.objects.filter(is_active=True).order_by('-created_at'),
        # ... rest of your existing context ...
    }
    return render(request, 'home.html', context)
