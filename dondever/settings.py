import os
from pathlib import Path
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY: get from env in production
SECRET_KEY = os.environ.get('SECRET_KEY', 'change-me-for-production')

# DEBUG should be False in production. Set via env var DEBUG=0/1 or true/false
DEBUG = os.environ.get('DEBUG', 'True').lower() in ('1', 'true', 'yes')

# ALLOWED_HOSTS: comma-separated list in env, e.g. "myapp.onrender.com,example.com"
ALLOWED_HOSTS = [h.strip() for h in os.environ.get('ALLOWED_HOSTS', '').split(',') if h.strip()]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'catalog',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'dondever.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'dondever.wsgi.application'

# Database configuration: prefer DATABASE_URL (Postgres on Supabase), fallback to sqlite for local dev
DATABASE_URL = os.environ.get('DATABASE_URL')
if DATABASE_URL:
    parsed_db = dj_database_url.parse(DATABASE_URL, conn_max_age=600)
    # Ensure SSL is used for Supabase/Postgres in production
    parsed_db.setdefault('OPTIONS', {})
    # If the URL doesn't already specify sslmode, require SSL
    if 'sslmode' not in DATABASE_URL:
        parsed_db['OPTIONS'].setdefault('sslmode', 'require')
    DATABASES = {'default': parsed_db}
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }

AUTH_PASSWORD_VALIDATORS = []

LANGUAGE_CODE = 'es-ar'

TIME_ZONE = 'America/Argentina/Buenos_Aires'

USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise static files storage for compressed files (helps on Render)
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# TMDB API key (leave empty and set via environment variable TMDB_API_KEY or fill here)
TMDB_API_KEY = os.environ.get('TMDB_API_KEY', 'f966b7e3d2a3791edbf0823b996c002e')
# Seconds to wait between TMDB requests to help avoid rate limits (float)
TMDB_REQUEST_DELAY = 0.10

# Security settings for production
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = True

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
