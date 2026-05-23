"""Check Cloudinary configuration."""

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Verify Cloudinary connectivity and media storage settings."

    def handle(self, *args, **options):
        self.stdout.write(f"USE_CLOUDINARY: {settings.USE_CLOUDINARY}")
        self.stdout.write(f"Storage backend: {settings.STORAGES['default']['BACKEND']}")
        self.stdout.write(f"MEDIA_ROOT: {settings.MEDIA_ROOT}")
        self.stdout.write(f"MEDIA_URL: {settings.MEDIA_URL}")

        if not settings.USE_CLOUDINARY:
            self.stdout.write(self.style.WARNING(
                "Cloudinary is disabled. Set CLOUDINARY_URL in Railway variables."
            ))
            return

        if settings.CLOUDINARY_URL:
            self.stdout.write("CLOUDINARY_URL: configured")
        else:
            self.stdout.write(
                f"Cloud name: {settings.CLOUDINARY_CLOUD_NAME or '(empty)'}"
            )

        try:
            import cloudinary.api

            cloudinary.api.ping()
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"Cloudinary ping failed: {exc}"))
            self.stdout.write(
                "Copy CLOUDINARY_URL exactly from Cloudinary Dashboard → Settings → API Keys."
            )
            return

        self.stdout.write(self.style.SUCCESS("Cloudinary connection OK."))
