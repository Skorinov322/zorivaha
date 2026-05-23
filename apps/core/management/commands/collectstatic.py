"""
Use Django's default collectstatic command.

cloudinary_storage overrides collectstatic and skips copying unhashed files
unless StaticCloudinaryStorage is configured. We serve static files with
WhiteNoise locally, so restore the standard behavior.
"""

from django.contrib.staticfiles.management.commands.collectstatic import Command

__all__ = ["Command"]
