from django.contrib import admin
from .models import WardenProfile


@admin.register(WardenProfile)
class WardenProfileAdmin(admin.ModelAdmin):
    list_display = (
        "employee_id",
        "user",
        "assigned_block",
    )

    search_fields = (
        "employee_id",
        "user__name",
        "user__email",
    )