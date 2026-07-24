from django.conf import settings


def site_settings(request):
    """Expose site-wide branding and config to all templates."""
    return {
        'SITE_NAME': settings.SITE_NAME,
        'SITE_TAGLINE': settings.SITE_TAGLINE,
        'SITE_CITY': settings.SITE_CITY,
        'SITE_COUNTRY': settings.SITE_COUNTRY,
    }
