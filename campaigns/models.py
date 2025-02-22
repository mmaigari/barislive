from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.contrib.auth import get_user_model
from django.utils import timezone

class CampaignCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True, blank=True)

    class Meta:
        verbose_name_plural = "Campaign Categories"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class Campaign(models.Model):
    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=200, unique=True, blank=True)
    category = models.ForeignKey(CampaignCategory, on_delete=models.CASCADE)
    short_description = models.TextField()
    description = models.TextField()
    image = models.ImageField(upload_to='campaigns/')
    goal_amount = models.DecimalField(max_digits=10, decimal_places=2)
    raised_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    def progress_percentage(self):
        return (self.raised_amount / self.goal_amount * 100) if self.goal_amount > 0 else 0

    def get_absolute_url(self):
        return reverse('campaigns:campaign-detail', kwargs={'slug': self.slug})

class Donation(models.Model):
    PAYMENT_STATUS = (
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    )

    campaign = models.ForeignKey('Campaign', on_delete=models.CASCADE)
    donor = models.ForeignKey(get_user_model(), on_delete=models.SET_NULL, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    is_anonymous = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS, default='pending')
    transaction_reference = models.CharField(max_length=200, unique=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.amount} by {self.donor or 'Anonymous'} for {self.campaign}"
