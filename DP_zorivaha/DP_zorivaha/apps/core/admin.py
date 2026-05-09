"""
Custom Django Admin configuration
"""
from django.contrib import admin
from django.contrib.admin import AdminSite


class CustomAdminSite(AdminSite):
    """Custom admin site with custom styling"""
    
    site_header = "Зори Ваха — Управление"
    site_title = "Зори Ваха"
    index_title = "Панель управления гостиницей"
    
    class Media:
        css = {
            'all': ('css/admin_custom.css',)
        }


# Replace default admin site
admin.site = CustomAdminSite()
admin.sites.site = admin.site
