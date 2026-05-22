# TBXR Frontend

## API Integration

Base URL (local dev): http://127.0.0.1:8000

Session auth (for POST requests):
- Cookie: `csrftoken=<token>; sessionid=<token>`
- X-CSRFToken: `<token>`
- Origin: http://127.0.0.1:8000
- Referer: http://127.0.0.1:8000/

Upload flow (server-triggered):
1. `POST /api/imaging/patients/<patient_id>/xray/upload/` (multipart `raw_image`)
2. `GET /api/imaging/xray/<transaction_id>/` (detail view)

Optional: `POST /api/imaging/xray/<transaction_id>/analyse/` to re-run AI inference.

### Core Endpoints

Auth:
- `GET /accounts/csrf-token/`
- `POST /accounts/login/`
- `POST /accounts/logout/`

Patients:
- `GET /api/patients/`
- `POST /api/patients/register/`
- `GET /api/patients/search/?name=<query>`
- `GET /api/patients/<patient_id>/`

Imaging:
- `POST /api/imaging/patients/<patient_id>/xray/upload/`
- `GET /api/imaging/patients/<patient_id>/xray/upload/confirm/<transaction_id>/`
- `POST /api/imaging/xray/<transaction_id>/analyse/`
- `GET /api/imaging/patients/<patient_id>/xray/`
- `GET /api/imaging/patients/<patient_id>/history/`
- `GET /api/imaging/dashboard/technologist/?page=&search=&status=`
- `GET /api/imaging/queue/?page=&search=&status=`
- `GET /api/imaging/xray/<transaction_id>/`
- `POST /api/imaging/xray/<transaction_id>/annotate/`

Schema & docs:
- `GET /api/schema/`
- `GET /api/docs/`

For full request/response details, see `backend/ENDPOINTS.md`.

# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and [`typescript-eslint`](https://typescript-eslint.io) in your project.
