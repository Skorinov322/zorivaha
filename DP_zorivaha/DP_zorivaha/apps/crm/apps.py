from django.apps import AppConfig


class CrmConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.crm"
    verbose_name = "CRM — управление клиентами"

    def ready(self):
        import apps.crm.signals
