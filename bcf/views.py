from django.views.generic import TemplateView
from cases.models import Case, Donation
from campaigns.models import Campaign
from sponsorships.models import Sponsorship
from django.db.models import Sum, Count
from django.contrib.auth import get_user_model
from django.shortcuts import render

class HomeView(TemplateView):
    template_name = 'home.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Add all campaigns query
        try:
            context['all_campaigns'] = Campaign.objects.filter(is_active=True).order_by('-created_at')
        except:
            context['all_campaigns'] = []
            
        # Get statistics with error handling
        try:
            context['total_cases'] = Case.objects.filter(is_active=True).count()
        except:
            context['total_cases'] = 0
            
        try:
            context['total_donors'] = get_user_model().objects.filter(
                donations__status='successful'
            ).distinct().count()
        except:
            context['total_donors'] = 0
            
        try:
            total_raised = Case.objects.aggregate(
                total=Sum('raised_amount')
            )['total']
            context['total_raised'] = total_raised or 0
        except:
            context['total_raised'] = 0
            
        try:
            context['countries_reached'] = Case.objects.filter(
                is_active=True
            ).values('country').distinct().count()
        except:
            context['countries_reached'] = 0
            
        # Get urgent cases
        try:
            context['urgent_cases'] = Case.objects.filter(
                is_active=True, 
                is_urgent=True
            )[:3]
        except:
            context['urgent_cases'] = []
            
        try:
            context['featured_campaigns'] = Campaign.objects.filter(
                is_active=True,
                is_featured=True
            )[:3]
        except:
            context['featured_campaigns'] = []
            
        try:
            context['featured_sponsorships'] = Sponsorship.objects.filter(
                status='active',
                is_featured=True
            )[:3]
        except:
            context['featured_sponsorships'] = []
            
        return context

def home(request):
    # ...existing view code...
    
    # Add these queries
    featured_campaigns = Campaign.objects.filter(
        is_active=True,
        is_featured=True
    )[:3]
    
    featured_sponsorships = Sponsorship.objects.filter(
        status='active',
        is_featured=True
    )[:3]
    
    context = {
        'featured_campaigns': featured_campaigns,
        'featured_sponsorships': featured_sponsorships,
        # ...existing context...
    }
    
    return render(request, 'home.html', context)

class AboutView(TemplateView):
    template_name = 'pages/about.html'

class ContactView(TemplateView):
    template_name = 'pages/contact.html'