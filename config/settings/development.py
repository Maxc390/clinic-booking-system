from .base import *

DEBUG = True

ALLOWED_HOSTS = ['*']

# Console email backend for testing
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
