from django.contrib import admin
from .models import CleanerProfile


@admin.register(CleanerProfile)
class CleanerProfileAdmin(admin.ModelAdmin):
    list_display = (
        "employee_id",
        "user",
        "assigned_block",
        "is_available",
    )

    list_filter = (
        "assigned_block",
        "is_available",
    )

    search_fields = (
        "employee_id",
        "user__name",
        "user__email",
    )