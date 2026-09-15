# Security Environment Profile

This document defines the required environment-hygiene baseline for TB-XR deployments.

## Rules

- Never commit real secrets to source control.
- Keep backend/.env local-only; commit placeholders in backend/.env.example and backend/.env.production.example.
- Store production secrets in an external secret manager or protected CI/CD variables.
- Rotate secrets immediately if exposure is suspected.

## Required Production Variables

- SECRET_KEY
- ALLOWED_HOSTS
- CSRF_TRUSTED_ORIGINS
- DB_NAME
- DB_USER
- DB_PASSWORD
- DB_HOST
- DB_PORT

## Production Safety Defaults

- DEBUG=false
- SESSION_COOKIE_SECURE=true
- CSRF_COOKIE_SECURE=true
- SECURE_SSL_REDIRECT=true (when behind HTTPS)
- USE_X_FORWARDED_PROTO=true (when using a reverse proxy)

## Django Production Guardrails

- DJANGO_ENV=production enforces DEBUG=false.
- ALLOWED_HOSTS must be explicitly set and cannot contain localhost/testserver values.
- CSRF_TRUSTED_ORIGINS must be explicitly set and use https:// origins only.
- HSTS, frame, and content-type hardening defaults are enabled for production.

## Trusted Host And CSRF Matrix

- App URL example: https://app.example.com
- API URL example: https://api.example.com
- ALLOWED_HOSTS: api.example.com
- CSRF_TRUSTED_ORIGINS: https://app.example.com,https://api.example.com

Use the smallest possible origin list to reduce cross-site request risk.

## Verification Checklist

1. Confirm no live secrets are present in tracked files.
2. Confirm backend/.env is ignored and not tracked.
3. Confirm backend/.env.production.example contains placeholders only.
4. Confirm app starts using only environment-provided settings.
5. Confirm deployment docs point to external secret storage.
6. Run `python manage.py check --deploy` with production env values.
