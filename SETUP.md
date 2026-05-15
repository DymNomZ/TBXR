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

create_role_user("tech1", "demo123", "RADIOLOGIC_TECH", "tech1@example.com")
create_role_user("rad1", "demo123", "RADIOLOGIST", "rad1@example.com")
create_role_user("phys1", "demo123", "PHYSICIAN", "phys1@example.com")
```
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

For testing Back end automatically.
``` bash
cd backend
python manage.py test apps.accounts.tests
```

---
