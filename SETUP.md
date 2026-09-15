## Setup

### Prerequisites
- Python 3.11+
- Node.js 20+ and npm
- PostgreSQL 15+
- Git

---

### Backend Setup

```bash
# 1. Navigate into backend
cd backend

# 2. Create and activate virtual environment
python -m venv venv
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

# 3. Install dependencies
python -m pip install -r requirements.txt
or
py -m pip install -r requirements.txt

# 4. Set up environment variables
cp .env.example .env
# Open .env and fill in DB credentials and SECRET_KEY

# 5. Run migrations
python manage.py migrate

# 6. Create a superuser (for admin access)
python manage.py createsuperuser

# 7. Start the development server
python manage.py runserver
```

The backend runs at `http://localhost:8000`

> **Note:** All Django management commands (`migrate`, `createsuperuser`, `startapp`, etc.) are run from inside the `backend/` folder where `manage.py` lives.

### Database Options

The backend chooses its database from the values in `backend/.env`:

- If `DB_NAME` is set, Django uses PostgreSQL with `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT`.
- If `DB_NAME` is not set, Django falls back to SQLite at `backend/db.sqlite3`.

So yes, if you want a different PostgreSQL database, you should change the `.env` file.
For example, update `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT` to match the target database.

If you want to use SQLite for a local throwaway setup, remove `DB_NAME` from `.env`.

Example PostgreSQL `.env` values:

```env
SECRET_KEY=<set-a-strong-random-secret>
DB_NAME=<postgres-db-name>
DB_USER=<postgres-db-user>
DB_PASSWORD=<postgres-db-password>
DB_HOST=localhost
DB_PORT=5432
```

Example SQLite `.env` values:

```env
SECRET_KEY=<set-a-strong-random-secret>
```

### Switching Databases For SUS Testing

Use this workflow when you want a clean PostgreSQL database for SUS sessions.

1. Create the PostgreSQL role and database.

```bash
sudo -u postgres psql
```

```sql
CREATE USER <sus_db_user> WITH PASSWORD '<sus_db_password>';
CREATE DATABASE <sus_db_name> OWNER <sus_db_user>;
GRANT ALL PRIVILEGES ON DATABASE <sus_db_name> TO <sus_db_user>;
\q
```

2. Update `backend/.env` to point to the SUS database.

```env
SECRET_KEY=<set-a-strong-random-secret>
DB_NAME=<sus-db-name>
DB_USER=<sus-db-user>
DB_PASSWORD=<sus-db-password>
DB_HOST=localhost
DB_PORT=5432
```

3. Start a fresh terminal session or unset any old `DB_*` environment variables.

```bash
unset DB_NAME DB_USER DB_PASSWORD DB_HOST DB_PORT SECRET_KEY
```

4. Run migrations against the SUS database.

```bash
cd backend
python manage.py migrate
```

5. Seed the SUS users and patient pool.

```bash
python scripts/seed_sus_dataset.py
```

This script seeds:
- 1 technologist user
- 1 radiologist user
- 5 patients

It does not create X-ray records, images, annotations, or AI results. Those
are added manually during the SUS walkthrough.

**Important:** If you create PostgreSQL roles or databases without quotes, PostgreSQL stores the names in lowercase. Use lowercase values in `.env` unless you intentionally created quoted mixed-case identifiers.

### Switching Back To The Original Database

To return to the original development database, reverse the same steps:

1. Restore the old values in `backend/.env`.

```env
SECRET_KEY=<set-a-strong-random-secret>
DB_NAME=<postgres-db-name>
DB_USER=<postgres-db-user>
DB_PASSWORD=<postgres-db-password>
DB_HOST=localhost
DB_PORT=5432
```

2. Clear any exported shell variables that might override `.env`.

```bash
unset DB_NAME DB_USER DB_PASSWORD DB_HOST DB_PORT SECRET_KEY
```

3. Run migrations again so Django connects to the original database.

```bash
cd backend
python manage.py migrate
```

4. If needed, re-run seed or demo setup scripts for the original database.

---

### Frontend Setup

```bash
# 1. Navigate into frontend
cd frontend

# 2. Install dependencies
npm install

# 3. Start the development server
npm run dev
```

The frontend runs at `http://localhost:5173`

> **Note:** The frontend talks to the backend via Axios. API base URL is configured in `src/services/api.js`. Make sure the backend is running when testing the frontend.

---

### AI Setup (Seth)

```bash
# 1. Navigate into ai/
cd ai

# 2. Create a separate virtual environment (keep AI deps isolated)
python -m venv venv
source venv/bin/activate

# 3. Install AI dependencies
pip install -r requirements.txt

# 4. Launch Jupyter
jupyter notebook notebooks/
```

> **Note:** Trained model weights go in `ai/weights/`. Add large `.pt` files to `.gitignore` and share via Google Drive or a shared storage link instead.

---

### Front End and Back End Testing

For testing Front and Back end manually.
``` bash
cd backend

# ignore if you have done this already
source venv/bin/activate        # Linux/macOS
venv\Scripts\activate           # Windows

#ignore if you have done this already
python -m pip install -r requirements.txt
or
py -m pip install -r requirements.txt

#ignore if you have done this already
cp .env.example .env

python manage.py migrate
python manage.py shell
```

To seed account to test login functionality.
``` bash
from django.contrib.auth import get_user_model

User = get_user_model()

def create_role_user(username, password, role, email=""):
    user, created = User.objects.get_or_create(
        username=username,
        defaults={
            "email": email,
            "role": role,
        },
    )
    if not created:
        user.role = role
        if email:
            user.email = email
    user.set_password(password)
    user.save()
    return user

create_role_user("tech1", "<local-test-password>", "RADIOLOGIC_TECH", "tech1@example.com")
create_role_user("rad1", "<local-test-password>", "RADIOLOGIST", "rad1@example.com")
```

For local demo accounts, choose your own non-production test password and never reuse real credentials.
``` bash
python manage.py runserver
```

Then set up the front end if you have not yet already.
``` bash
cd frontend
npm install 
# npm install vite lucide-react
npm run dev
```

**Note**: If you want to check the database structure with GUI you can download DBeaver and connect the PostgreSQL there. Use the .env variables you have set.

### Backup and Restore

Automated database + media backups and the restore procedure are documented in
[`documentation/backup-restore.md`](../documentation/backup-restore.md).

```bash
cd backend
python scripts/backup.py                         # create a backup
python scripts/backup.py --verify backups/<ts>   # verify integrity
python scripts/restore.py                        # dry-run latest backup
python scripts/restore.py <backup-dir> --apply   # apply a restore
```

## Environment Security Rules

- Never commit real secrets or credentials (for example: SECRET_KEY, DB_PASSWORD, API keys).
- Keep `.env` local-only; commit placeholders in `.env.example` only.
- Store production secrets in your deployment platform secret manager or protected CI/CD variables.
- Rotate credentials immediately if a secret is exposed.

For testing Back end automatically.
``` bash
cd backend
python manage.py test apps.accounts.tests
python manage.py test apps.patients.tests
python manage.py test apps.imaging.tests
```

---
