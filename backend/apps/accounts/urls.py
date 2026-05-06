from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('csrf-token/', views.csrf_token_view, name='csrf-token'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/technologist/', views.technologist_dashboard, name='technologist-dashboard'),
    path('dashboard/radiologist/', views.radiologist_dashboard, name='radiologist-dashboard'),
    path('dashboard/physician/', views.physician_dashboard, name='physician-dashboard'),
]