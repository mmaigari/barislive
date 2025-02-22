from django.urls import path
from . import views

app_name = 'cases'

urlpatterns = [
    path('', views.CaseListView.as_view(), name='case-list'),
    path('create/', views.CaseCreateView.as_view(), name='case-create'),
    path('<slug:slug>/', views.CaseDetailView.as_view(), name='case-detail'),
    path('<slug:slug>/update/', views.CaseUpdateView.as_view(), name='case-update'),
    path('<slug:slug>/delete/', views.CaseDeleteView.as_view(), name='case-delete'),
    path('<int:case_id>/donate/', views.initiate_donation, name='initiate-donation'),
    path('webhook/flutterwave/', views.flutterwave_webhook, name='flutterwave-webhook'),
    path('payment/verify/', views.verify_payment, name='verify-payment'),
    path('payment/success/', views.PaymentSuccessView.as_view(), name='payment-success'),
]
