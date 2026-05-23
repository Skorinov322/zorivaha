"""Helpers for user-uploaded media (Cloudinary / local storage)."""

from __future__ import annotations


def media_upload_error_message(exc: Exception) -> str:
    """Turn storage/Cloudinary failures into a user-facing Russian message."""
    text = str(exc).strip()
    lower = text.lower()

    if "invalid signature" in lower or "invalid api key" in lower:
        return (
            "Не удалось загрузить фото: ошибка настройки Cloudinary на сервере. "
            "Проверьте переменную CLOUDINARY_URL в панели хостинга."
        )
    if "unauthorized" in lower or "401" in lower:
        return (
            "Не удалось загрузить фото: Cloudinary отклонил запрос. "
            "Проверьте API-ключ и секрет в CLOUDINARY_URL."
        )
    if "file size" in lower or "too large" in lower:
        return "Файл слишком большой. Загрузите изображение меньшего размера."
    if text:
        return f"Не удалось загрузить фото: {text}"
    return "Не удалось загрузить фото. Попробуйте другой файл или повторите позже."
