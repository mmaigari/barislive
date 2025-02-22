from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from decimal import Decimal

class SponsorshipCategory(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField()
    image = models.ImageField(upload_to='sponsorship_categories/')
    
    class Meta:
        verbose_name_plural = 'Sponsorship Categories'
        
    def __str__(self):
        return self.name
        
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

class Sponsorship(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('pending', 'Pending'),
    )
    
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    category = models.ForeignKey(SponsorshipCategory, on_delete=models.CASCADE)
    description = models.TextField()
    beneficiary_name = models.CharField(max_length=100)
    beneficiary_age = models.PositiveIntegerField()
    monthly_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))]
    )
    total_sponsors = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to='sponsorships/')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    is_featured = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
        
    def __str__(self):
        return self.title
        
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
        
    def get_absolute_url(self):
        return reverse('sponsorships:sponsorship-detail', kwargs={'slug': self.slug})

class SponsorshipPayment(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('success', 'Success'),
        ('failed', 'Failed'),
    )
    
    sponsorship = models.ForeignKey(Sponsorship, on_delete=models.CASCADE)
    sponsor = models.ForeignKey(User, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    months = models.PositiveIntegerField(default=1)
    transaction_reference = models.CharField(max_length=100, unique=True)
    payment_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_anonymous = models.BooleanField(default=False)
    is_recurring = models.BooleanField(default=False)
    next_payment_date = models.DateField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.sponsor.email} - {self.sponsorship.title}"
