from django.urls import path
from . import views

app_name = 'sponsorships'

urlpatterns = [
    path('', views.sponsorship_list, name='sponsorship-list'),
    path('payment/verify/', views.verify_payment, name='verify-payment'),
    path('<int:sponsorship_id>/process/', views.process_sponsorship, name='process-sponsorship'),
    path('<slug:slug>/', views.sponsorship_detail, name='sponsorship-detail'),
]