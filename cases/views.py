from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView, DetailView, TemplateView, CreateView, UpdateView, DeleteView
from django.db.models import Sum
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST, require_GET
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction
import json
import logging
from .models import Case, Donation
from .services import FlutterwaveService
from django.conf import settings
from .utils import initialize_flutterwave_payment, verify_flutterwave_payment
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse_lazy

logger = logging.getLogger(__name__)

class CaseListView(ListView):
    model = Case
    template_name = 'cases/case_list.html'
    context_object_name = 'cases'
    paginate_by = 12
    
    def get_queryset(self):
        return Case.objects.filter(is_active=True).order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add category stats
        context['total_cases'] = Case.objects.filter(is_active=True).count()
        context['medical_cases'] = Case.objects.filter(
            is_active=True, 
            category='medical'
        ).count()
        context['humanitarian_cases'] = Case.objects.filter(
            is_active=True, 
            category='humanitarian'
        ).count()
        
        # Add financial stats
        context['total_goal'] = Case.objects.filter(
            is_active=True
        ).aggregate(Sum('goal_amount'))['goal_amount__sum'] or 0
        context['total_raised'] = Case.objects.filter(
            is_active=True
        ).aggregate(Sum('raised_amount'))['raised_amount__sum'] or 0
        
        # Active category
        context['active_category'] = self.request.GET.get('category', 'all')
        
        context['categories'] = Case.objects.values('category').distinct()
        
        return context

class CaseDetailView(DetailView):
    model = Case
    template_name = 'cases/case_detail.html'
    context_object_name = 'case'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Add related cases (same category)
        context['related_cases'] = Case.objects.filter(
            category=self.object.category,
            is_active=True
        ).exclude(id=self.object.id)[:3]
        context['donations'] = self.object.donations.filter(
            status='successful'
        ).select_related('donor')[:10]  # Get last 10 successful donations
        return context

class CaseCreateView(LoginRequiredMixin, CreateView):
    model = Case
    template_name = 'cases/case_form.html'
    fields = ['title', 'description', 'category', 'amount_needed', 'image']
    success_url = reverse_lazy('cases:case-list')

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        return super().form_valid(form)

class CaseUpdateView(LoginRequiredMixin, UpdateView):
    model = Case
    template_name = 'cases/case_form.html'
    fields = ['title', 'description', 'category', 'amount_needed', 'image']
    
    def get_success_url(self):
        return reverse_lazy('cases:case-detail', kwargs={'slug': self.object.slug})

class CaseDeleteView(LoginRequiredMixin, DeleteView):
    model = Case
    template_name = 'cases/case_confirm_delete.html'
    success_url = reverse_lazy('cases:case-list')

class PaymentSuccessView(LoginRequiredMixin, TemplateView):
    template_name = 'cases/payment_success.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        tx_ref = self.request.GET.get('tx_ref')
        
        if tx_ref:
            try:
                donation = Donation.objects.select_related('case').get(
                    transaction_id=tx_ref
                )
                context['donation'] = donation
            except Donation.DoesNotExist:
                pass
                
        return context

@login_required
@require_POST
def initiate_donation(request, case_id):
    try:
        case = Case.objects.get(id=case_id)
        data = json.loads(request.body)
        
        # Validate email
        if not request.user.email:
            return JsonResponse({
                'status': 'error',
                'message': 'Email address is required'
            }, status=400)
        
        # Validate amount
        try:
            amount = float(data.get('amount', 0))
            if amount < 1:
                raise ValueError("Minimum donation amount is $1")
        except (TypeError, ValueError):
            return JsonResponse({
                'status': 'error',
                'message': 'Invalid donation amount'
            }, status=400)
        
        is_anonymous = data.get('is_anonymous', False)
        
        # Initialize payment
        payment_data = initialize_flutterwave_payment(
            user=request.user,
            case=case,
            amount=amount,
            is_anonymous=is_anonymous
        )
        
        # Create pending donation
        donation = Donation.objects.create(
            case=case,
            donor=request.user,
            amount=amount,
            transaction_id=payment_data['tx_ref'],  # Use tx_ref from our payload
            status='pending',
            is_anonymous=is_anonymous
        )
        
        logger.info(f"Created donation {donation.id} with tx_ref {payment_data['tx_ref']}")
        
        return JsonResponse({
            'status': 'success',
            'payment_link': payment_data['data']['link']
        })
        
    except Case.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'message': 'Case not found'
        }, status=404)
    except ValueError as e:
        logger.error(f"Validation error: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }, status=400)
    except Exception as e:
        logger.error(f"Donation error: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'An error occurred while processing your request'
        }, status=500)

@csrf_exempt
def flutterwave_webhook(request):
    if request.method != 'POST':
        return HttpResponse(status=405)
    
    signature = request.headers.get('verif-hash')
    if not signature or signature != settings.FLUTTERWAVE_SECRET_HASH:
        return HttpResponse(status=401)
    
    try:
        data = json.loads(request.body)
        if data['status'] == 'successful':
            tx_ref = data['txRef']
            
            with transaction.atomic():
                donation = Donation.objects.select_related('case').get(
                    transaction_id=tx_ref,
                    status='pending'
                )
                
                donation.status = 'successful'
                donation.save()
                
                # Update case raised amount
                donation.case.raised_amount += donation.amount
                donation.case.save()
                
        return HttpResponse(status=200)
        
    except Exception as e:
        return HttpResponse(str(e), status=400)

@require_GET
def verify_payment(request):
    """Handle payment verification callback from Flutterwave"""
    status = request.GET.get('status')
    tx_ref = request.GET.get('tx_ref')
    transaction_id = request.GET.get('transaction_id')
    
    logger.info(f"Payment callback: status={status}, tx_ref={tx_ref}, transaction_id={transaction_id}")
    
    try:
        donation = Donation.objects.select_related('case').get(transaction_id=tx_ref)
        
        if status == 'successful':
            # Verify with Flutterwave
            verification = verify_flutterwave_payment(transaction_id)
            
            if verification['status'] == 'success':
                with transaction.atomic():
                    # Update donation status
                    donation.status = 'successful'
                    donation.flw_transaction_id = transaction_id
                    donation.save()
                    
                    # Update case raised amount
                    case = donation.case
                    case.raised_amount = case.raised_amount + donation.amount
                    case.save()
                    
                    messages.success(
                        request, 
                        'Thank you for your donation! Your payment has been processed successfully.'
                    )
                    
                    logger.info(f"Payment successful: tx_ref={tx_ref}, amount={donation.amount}")
            else:
                donation.status = 'failed'
                donation.save()
                messages.error(
                    request, 
                    'Payment verification failed. Please contact support if you believe this is an error.'
                )
                logger.error(f"Payment verification failed: {verification.get('message')}")
        else:
            donation.status = 'failed'
            donation.save()
            messages.warning(request, 'Payment was cancelled or unsuccessful.')
            logger.warning(f"Payment unsuccessful: status={status}, tx_ref={tx_ref}")
        
        return redirect('cases:case-detail', slug=donation.case.slug)
        
    except Donation.DoesNotExist:
        logger.error(f"Donation not found for tx_ref: {tx_ref}")
        messages.error(
            request, 
            'Could not find the associated donation. Please contact support.'
        )
        return redirect('home')
        
    except Exception as e:
        logger.error(f"Payment verification error: {str(e)}")
        messages.error(
            request, 
            'An error occurred while processing your payment. Please contact support.'
        )
        return redirect('home')
