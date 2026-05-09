from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Ядро"
    
    def ready(self):
        """Import custom admin configuration"""
        from apps.core import admin  # noqa
