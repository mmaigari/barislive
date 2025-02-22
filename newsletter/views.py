from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_protect
from .models import NewsletterSubscription

# Create your views here.

@require_POST
@csrf_protect
def subscribe_newsletter(request):
    try:
        email = request.POST.get('email')
        if not email:
            return JsonResponse({'status': 'error', 'message': 'Email is required'}, status=400)
        
        # Check if already subscribed
        if NewsletterSubscription.objects.filter(email=email).exists():
            return JsonResponse({
                'status': 'info',
                'message': 'You are already subscribed to our newsletter!'
            })
        
        # Create new subscription
        NewsletterSubscription.objects.create(email=email)
        
        return JsonResponse({
            'status': 'success',
            'message': 'Thank you for subscribing to our newsletter!'
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': 'An error occurred. Please try again later.'
        }, status=500)
