# This file contains decorators for role-based access control in the accounts app.
# To use these decorators, simply import them and apply to your views. For example:
# from .decorators import role_required
# @role_required(UserRole.RADIOLOGIC_TECH, UserRole.RADIOLOGIST)
# def my_view(request):
#     ...
# Ensure to use this decorator in conjunction with Django's built-in @login_required to all protected views.
# - Dymes, 2024-06-15
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from functools import wraps
from django.http import JsonResponse
from django.conf import settings
from functools import wraps

from apps.accounts.enums import UserRole

def role_required(*allowed_roles):
    def decorator(view_func):
        # Yours delegates the unauthenticated case to Django's built-in @login_required.
        # This respects the LOGIN_URL setting in settings.py
        @login_required
        # This preserves the original function's __name__ and __doc__ metadata after wrapping. 
        # Without it, the views look like _wrapped_view in stack traces and Django's URL resolver, 
        # which makes debugging painful. 
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # Check role
            user_role = request.user.role
            normalized_roles = [r.value if hasattr(r, 'value') else r for r in UserRole]
            if user_role not in normalized_roles:
                raise PermissionDenied
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def staff_or_debug_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if settings.DEBUG:
            return view_func(request, *args, **kwargs)
        if not request.user.is_authenticated or not request.user.is_staff:
            return JsonResponse(
                {'error': 'You do not have permission to access this resource.'},
                status=403
            )
        return view_func(request, *args, **kwargs)
    return _wrapped_view