from django.contrib import admin
from .models import CleaningRequest, Feedback


@admin.register(CleaningRequest)
class CleaningRequestAdmin(admin.ModelAdmin):
    list_display = (
        "student",
        "hostel_allocation",
        "cleaning_date",
        "time_slot",
        "cleaning_type",
        "status",
        "assigned_cleaner",
    )

    list_filter = (
        "status",
        "cleaning_date",
        "cleaning_type",
        "hostel_allocation__block",
    )

    search_fields = (
        "student__user__email",
        "student__user__name",
        "hostel_allocation__room_number",
    )


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = (
        "cleaning_request",
        "room_status",
        "rating",
        "created_at",
    )

    list_filter = (
        "room_status",
        "rating",
    )
