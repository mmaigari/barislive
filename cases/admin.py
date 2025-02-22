from django.contrib import admin
from .models import Case, Donation

@admin.register(Case)
class CaseAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'status', 'goal_amount', 'raised_amount', 'created_at', 'is_active')
    list_filter = ('category', 'status', 'is_active')
    search_fields = ('title', 'short_description')
    prepopulated_fields = {'slug': ('title',)}

@admin.register(Donation)
class DonationAdmin(admin.ModelAdmin):
    list_display = ['case', 'donor', 'amount', 'currency', 'status', 'created_at']
    list_filter = ['status', 'currency', 'created_at']
    search_fields = ['case__title', 'donor__username', 'transaction_id']
    readonly_fields = ['transaction_id', 'created_at', 'modified_at']