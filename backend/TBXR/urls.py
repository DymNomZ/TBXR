"""
URL configuration for TBXR project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
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
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView
from apps.accounts.decorators import staff_or_debug_required
from apps.imaging.views import physician_dashboard, analytics_summary, analytics_export

schema_view = staff_or_debug_required(SpectacularAPIView.as_view())
docs_view   = staff_or_debug_required(SpectacularSwaggerView.as_view(url_name='schema'))

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('apps.accounts.urls')),
    path('api/patients/', include('apps.patients.urls')),
    path('api/imaging/', include('apps.imaging.urls')),
    path('api/analytics/summary/', analytics_summary, name='analytics_summary'),
    path('api/analytics/export/', analytics_export, name='analytics_export'),
    path('api/physician/dashboard', physician_dashboard, name='physician_dashboard_root'),
    path('api/physician/dashboard/', physician_dashboard, name='physician_dashboard_root_slash'),
    path('api/schema/', schema_view, name='schema'),
    path('api/docs/', docs_view, name='swagger-ui'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
