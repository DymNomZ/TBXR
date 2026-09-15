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

## Verification Checklist

1. Confirm no live secrets are present in tracked files.
2. Confirm backend/.env is ignored and not tracked.
3. Confirm backend/.env.production.example contains placeholders only.
4. Confirm app starts using only environment-provided settings.
5. Confirm deployment docs point to external secret storage.
