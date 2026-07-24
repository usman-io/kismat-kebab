# Kismat Kebabs

Fast food delivery & collection platform for **Hull, England** — built with Django Templates and SQLite.

## Tech Stack

- **Backend:** Django 6.x
- **Database:** SQLite
- **Templates:** Django Templates (server-rendered)
- **Email:** [MailerSend API](https://developers.mailersend.com/)
- **Frontend:** Custom CSS (no framework — lightweight & fast)

## Project Structure

```
QismatTakeaway/
├── config/              # Django project settings & URLs
├── accounts/            # Users, roles, email verification
├── core/                # Shared services (MailerSend), context processors
├── store/               # Customer-facing storefront
├── templates/           # Global Django templates
├── static/              # CSS, JS, images
├── media/               # User uploads (menu images, etc.)
├── manage.py
├── requirements.txt
└── .env.example
```

## User Roles

| Role     | Created by        | Access                          |
|----------|-------------------|---------------------------------|
| Customer | Self-registration | Menu, cart, orders, favourites  |
| Admin    | Superuser         | Full admin panel                |
| Staff    | Admin             | Kitchen, order management       |

## Quick Start

### 1. Clone & set up environment

```bash
cd QismatTakeaway
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your SECRET_KEY and MailerSend API token
```

### 3. Run migrations

```bash
python manage.py migrate
```

### 4. Create admin superuser

```bash
python manage.py createsuperuser
```

### 5. Start development server

```bash
python manage.py runserver
```

Visit **http://127.0.0.1:8000** for the customer homepage.  
Visit **http://127.0.0.1:8000/admin/** for Django admin.

## MailerSend Setup

1. Create an account at [mailersend.com](https://www.mailersend.com/)
2. Verify your sending domain
3. Generate an API token
4. Add to `.env`:

```
MAILERSEND_API_TOKEN=your-token-here
MAILERSEND_FROM_EMAIL=noreply@yourdomain.com
MAILERSEND_FROM_NAME=Kismat Kebabs
```

## License

Private project — Kismat Kebabs, Hull.
# kismat-kebab
