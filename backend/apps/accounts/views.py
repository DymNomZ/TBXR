import json

from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.http import HttpResponse, JsonResponse
from django.middleware.csrf import get_token
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.accounts.enums import UserRole

from .decorators import role_required


ROLE_FRONTEND_URLS = {
    UserRole.RADIOLOGIC_TECH: '/dashboard/technologist',
    UserRole.RADIOLOGIST:     '/dashboard/radiologist',
	UserRole.PHYSICIAN:       '/dashboard/physician',
	UserRole.PATIENT:         '/dashboard/patient',
}


def _parse_login_payload(request):
	content_type = request.headers.get('Content-Type', '')
	if 'application/json' in content_type:
		try:
			return json.loads(request.body.decode('utf-8') or '{}')
		except json.JSONDecodeError:
			return None
	return request.POST


@require_http_methods(['GET'])
def csrf_token_view(request):
	get_token(request)
	return JsonResponse({'detail': 'CSRF cookie set.'})


def _dashboard_response(title, role_label, message):
	logout_url = reverse('accounts:logout')
	html = f"""<!doctype html>
<html lang="en">
  <head>
	<meta charset="utf-8">
	<meta name="viewport" content="width=device-width, initial-scale=1">
	<title>{title}</title>
  </head>
  <body>
	<main>
	  <h1>{title}</h1>
	  <p>{message}</p>
	  <p>Current role: {role_label}</p>
	  <p><a href="{logout_url}">Logout</a></p>
	</main>
  </body>
</html>"""
	return HttpResponse(html, content_type='text/html')


@require_http_methods(['POST'])
def login_view(request):
	payload = _parse_login_payload(request)
	if payload is None:
		return JsonResponse({'error': 'Invalid JSON payload.'}, status=400)

	username = (payload.get('username') or '').strip()
	password = payload.get('password') or ''

	if not username or not password:
		return JsonResponse(
			{'error': 'Both username and password are required.'},
			status=400,
		)

	user = authenticate(request, username=username, password=password)
	if user is None:
		return JsonResponse(
			{'error': 'Invalid username or password.'},
			status=401,
		)

	login(request, user)

	frontend_url = ROLE_FRONTEND_URLS.get(user.role)
	if frontend_url is None:
		return JsonResponse(
			{'error': f'No dashboard configured for role "{user.role}".'},
			status=400,
		)
	return JsonResponse({
		'redirect': frontend_url,
		'role': user.role,
	}, status=200)

@require_http_methods(['POST'])
def logout_view(request):
    # Free any review locks held by this user so cases are not left blocked.
    if request.user.is_authenticated:
        from apps.imaging.models import XrayRecord
        for record in XrayRecord.objects.filter(active_reviewer=request.user):
            record.release_lock()
    logout(request)
    return JsonResponse({'detail': 'Logged out.'})

@role_required(UserRole.RADIOLOGIC_TECH)
def technologist_dashboard(request):
	return _dashboard_response(
		'Technologist Dashboard',
		'Radiologic Technologist',
		'This dashboard will show uploaded X-ray records for the logged-in technologist.',
	)


@role_required(UserRole.RADIOLOGIST)
def radiologist_dashboard(request):
	return _dashboard_response(
		'Radiologist Dashboard',
		'Radiologist',
		'This placeholder dashboard is ready for radiologist review workflows.',
	)
