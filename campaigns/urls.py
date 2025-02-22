from django.urls import path
from . import views

app_name = 'campaigns'

urlpatterns = [
    path('', views.campaign_list, name='campaign-list'),
    path('<int:campaign_id>/donate/', views.process_donation, name='process_donation'),
    path('webhook/flutterwave/', views.flutterwave_webhook, name='flutterwave-webhook'),
    path('payment/verify/', views.verify_payment, name='verify-payment'),
    path('<slug:slug>/', views.campaign_detail, name='campaign-detail'),
]