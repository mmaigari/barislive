from django.contrib import admin
from .models import SponsorshipCategory, Sponsorship, SponsorshipPayment

@admin.register(SponsorshipCategory)
class SponsorshipCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)

@admin.register(Sponsorship)
class SponsorshipAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'beneficiary_name', 'monthly_amount', 
                   'total_sponsors', 'status', 'is_featured')
    list_filter = ('status', 'category', 'is_featured')
    search_fields = ('title', 'beneficiary_name', 'description')
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('status', 'is_featured')
    date_hierarchy = 'created_at'

@admin.register(SponsorshipPayment)
class SponsorshipPaymentAdmin(admin.ModelAdmin):
    list_display = ('sponsor', 'sponsorship', 'amount', 'status', 
                   'payment_date', 'is_recurring')
    list_filter = ('status', 'is_recurring', 'is_anonymous')
    search_fields = ('sponsor__email', 'sponsorship__title', 'transaction_reference')
    date_hierarchy = 'payment_date'
    readonly_fields = ('transaction_reference', 'payment_date')
