from .base import *

DEBUG = True

# CORS configuration for local development
CORS_ALLOW_ALL_ORIGINS = True

# Development email backend (prints to terminal console)
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"