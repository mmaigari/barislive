"""
URL configuration for bcf project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from .views import HomeView, AboutView, ContactView
from users import views as user_views

urlpatterns = [
    path('', HomeView.as_view(), name='home'),
    path('admin/', admin.site.urls),
    path('cases/', include('cases.urls')),
    path('accounts/login/', auth_views.LoginView.as_view(), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('accounts/', include('django.contrib.auth.urls')),  # Add authentication URLs
    path('users/', include('users.urls', namespace='users')),
    path('about/', AboutView.as_view(), name='about'),
    path('campaigns/', include('campaigns.urls', namespace='campaigns')),
    path('sponsorships/', include('sponsorships.urls', namespace='sponsorships')),
    path('register/', user_views.register, name='register'),
    path('contact/', ContactView.as_view(), name='contact'),
    path('newsletter/', include('newsletter.urls', namespace='newsletter')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
