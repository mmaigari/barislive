from django.db import models
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify
from django.urls import reverse

class Case(models.Model):
    CATEGORY_CHOICES = [
        ('medical', 'Medical Case'),
        ('humanitarian', 'Humanitarian Case'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('urgent', 'Urgent'),
    ]

    RESPONSIBLE_SECTIONS = [
        ('medical', 'Medical Support Program'),
        ('humanitarian', 'Humanitarian Aid Program'),
    ]
    
    FUNDING_STATUS = [
        ('not_funded', 'Not Funded'),
        ('partially_funded', 'Partially Funded'),
        ('fully_funded', 'Fully Funded'),
    ]

    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True)
    short_description = models.TextField(max_length=500)
    full_description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    responsible_section = models.CharField(
        max_length=50, 
        choices=RESPONSIBLE_SECTIONS,
        default='medical'
    )
    funding_status = models.CharField(
        max_length=20,
        choices=FUNDING_STATUS,
        default='not_funded'
    )
    
    # Financial fields
    goal_amount = models.DecimalField(max_digits=10, decimal_places=2)
    raised_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Media
    image = models.ImageField(upload_to='cases/')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    country = models.CharField(
        max_length=100,
        help_text="Country where the case is located",
        null=True,  # Make field optional in database
        blank=True  # Make field optional in forms
    )
    
    is_urgent = models.BooleanField(
        default=False,
        help_text="Mark this case as urgent"
    )
    
    target_date = models.DateField(
        null=True,
        blank=True,
        help_text="Target date for completing the fundraising"
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('cases:case-detail', kwargs={'slug': self.slug})  # Add namespace

    @property
    def progress_percentage(self):
        if self.goal_amount > 0:
            return min(int((self.raised_amount / self.goal_amount) * 100), 100)
        return 0

    @property 
    def amount_left(self):
        return max(self.goal_amount - self.raised_amount, 0)

    @property
    def days_left(self):
        if self.target_date:
            days = (self.target_date - timezone.now().date()).days
            return max(days, 0)
        return None

    @property
    def is_fully_funded(self):
        return self.raised_amount >= self.goal_amount

    @property
    def is_expired(self):
        if self.target_date:
            return timezone.now().date() > self.target_date
        return False

    def update_funding_status(self):
        """Update funding status based on raised amount"""
        percentage = self.progress_percentage
        
        if percentage >= 100:
            self.funding_status = 'fully_funded'
        elif percentage > 0:
            self.funding_status = 'partially_funded'
        else:
            self.funding_status = 'not_funded'
        
        self.save(update_fields=['funding_status'])

    def update_status(self):
        """Update case status based on various conditions"""
        if not self.is_active:
            return
            
        if self.is_expired:
            self.status = 'completed'
        elif self.is_fully_funded:
            self.status = 'completed'
        elif self.is_urgent:
            self.status = 'urgent'
        else:
            self.status = 'active'
            
        self.save(update_fields=['status'])

class Donation(models.Model):
    case = models.ForeignKey(Case, on_delete=models.CASCADE, related_name='donations')
    donor = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='donations'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_id = models.CharField(max_length=100, unique=True)
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('successful', 'Successful'),
            ('failed', 'Failed')
        ],
        default='pending'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    payment_method = models.CharField(max_length=50, blank=True)
    currency = models.CharField(max_length=3, default='USD')
    is_anonymous = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Donation of {self.amount} {self.currency} to {self.case.title}"