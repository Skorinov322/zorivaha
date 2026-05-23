"""Media storage backends."""

from __future__ import annotations

import logging

from django.conf import settings
from django.core.files.storage import FileSystemStorage

logger = logging.getLogger(__name__)


class ResilientMediaStorage(FileSystemStorage):
    """
    Upload to Cloudinary when configured; fall back to local MEDIA_ROOT on failure.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("location", settings.MEDIA_ROOT)
        kwargs.setdefault("base_url", settings.MEDIA_URL)
        super().__init__(*args, **kwargs)
        self._cloudinary = None
        if getattr(settings, "USE_CLOUDINARY", False):
            from cloudinary_storage.storage import MediaCloudinaryStorage

            self._cloudinary = MediaCloudinaryStorage()

    def _save(self, name, content):
        if self._cloudinary is not None:
            try:
                if hasattr(content, "seek"):
                    content.seek(0)
                saved_name = self._cloudinary._save(name, content)
                logger.info("Uploaded media to Cloudinary: %s", saved_name)
                return saved_name
            except Exception as exc:
                logger.warning(
                    "Cloudinary upload failed for %s, saving locally: %s",
                    name,
                    exc,
                )
                if hasattr(content, "seek"):
                    content.seek(0)
        return super()._save(name, content)

    def url(self, name):
        if name and super().exists(name):
            return super().url(name)
        if self._cloudinary is not None and name:
            try:
                if self._cloudinary.exists(name):
                    return self._cloudinary.url(name)
            except Exception:
                pass
        return super().url(name)

    def delete(self, name):
        deleted = False
        if self._cloudinary is not None and name:
            try:
                if self._cloudinary.exists(name):
                    self._cloudinary.delete(name)
                    deleted = True
            except Exception:
                pass
        if super().exists(name):
            super().delete(name)
            deleted = True
        return deleted

    def exists(self, name):
        if name and super().exists(name):
            return True
        if self._cloudinary is not None and name:
            try:
                return self._cloudinary.exists(name)
            except Exception:
                pass
        return False
