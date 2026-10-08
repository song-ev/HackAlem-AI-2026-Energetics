import os
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent
DEBUG = os.getenv('DJANGO_DEBUG', '1') == '1'
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', '').strip()
API_TOKEN = os.getenv('API_TOKEN', '')
if not DEBUG and (len(SECRET_KEY) < 50 or SECRET_KEY.startswith(('local-', 'replace-')) or not API_TOKEN):
    raise ImproperlyConfigured('Set a unique DJANGO_SECRET_KEY (at least 50 characters) and API_TOKEN for production.')
# Local-only default is ephemeral, never a published shared signing credential.
if not SECRET_KEY:
    SECRET_KEY = get_random_secret_key()
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', 'localhost,127.0.0.1,[::1],testserver').split(',')
INSTALLED_APPS = ['django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
                  'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
                  'weather_archive', 'forecasting']
MIDDLEWARE = ['django.middleware.security.SecurityMiddleware', 'django.contrib.sessions.middleware.SessionMiddleware',
              'django.middleware.common.CommonMiddleware', 'django.middleware.csrf.CsrfViewMiddleware',
              'django.contrib.auth.middleware.AuthenticationMiddleware', 'django.contrib.messages.middleware.MessageMiddleware',
              'django.middleware.clickjacking.XFrameOptionsMiddleware']
ROOT_URLCONF = 'config.urls'
TEMPLATES = [{'BACKEND': 'django.template.backends.django.DjangoTemplates', 'DIRS': [BASE_DIR / 'templates'],
              'APP_DIRS': True, 'OPTIONS': {'context_processors': ['django.template.context_processors.request',
              'django.contrib.auth.context_processors.auth', 'django.contrib.messages.context_processors.messages']}}]
WSGI_APPLICATION = 'config.wsgi.application'
DATABASES = {'default': {'ENGINE': 'django.db.backends.sqlite3', 'NAME': os.getenv('DJANGO_DB_PATH') or BASE_DIR / 'db.sqlite3', 'OPTIONS': {'timeout': 30}}}
LANGUAGE_CODE = 'ru'
TIME_ZONE = 'UTC'
USE_TZ = True
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
ML_BACKEND = os.getenv('ML_BACKEND', 'http')
ML_SERVICE_URL = os.getenv('ML_SERVICE_URL', '')
ML_METADATA_URL = os.getenv('ML_METADATA_URL', '')
ML_SERVICE_TOKEN = os.getenv('ML_SERVICE_TOKEN', '')
OPEN_METEO_FORECAST_URL = os.getenv('OPEN_METEO_FORECAST_URL', '')
OPEN_METEO_PREVIOUS_RUNS_URL = os.getenv('OPEN_METEO_PREVIOUS_RUNS_URL', '')
OPEN_METEO_API_KEY = os.getenv('OPEN_METEO_API_KEY', '')
HTTP_TIMEOUT = float(os.getenv('HTTP_TIMEOUT', '30'))
WEATHER_PUBLICATION_LAG_HOURS = 8
DATA_UPLOAD_MAX_MEMORY_SIZE = 2 * 1024 * 1024
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False
X_FRAME_OPTIONS = 'DENY'
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = os.getenv('DJANGO_SECURE_SSL_REDIRECT', '1') == '1'
