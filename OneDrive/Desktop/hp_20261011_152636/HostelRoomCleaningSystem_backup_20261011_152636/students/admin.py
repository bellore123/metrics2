from django.contrib import admin

from .models import HostelAllocation, Room, StudentProfile


@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "block",
        "room_number",
        "hostel_name",
        "created_at",
    )
    list_filter = (
        "block",
        "hostel_name",
    )
    search_fields = (
        "room_number",
        "block",
    )



@admin.register(StudentProfile)
class StudentProfileAdmin(admin.ModelAdmin):
    list_display = (
        "student_email",
        "student_name",
    )

    search_fields = (
        "user__email",
        "user__name",
    )

    def student_email(self, obj):
        return obj.user.email

    student_email.short_description = "Student Email"

    def student_name(self, obj):
        return obj.user.name

    student_name.short_description = "Student Name"


@admin.register(HostelAllocation)
class HostelAllocationAdmin(admin.ModelAdmin):
    list_display = (
        "student_email",
        "block",
        "room_number",
        "academic_year",
        "is_current",
        "created_at",
    )

    list_filter = (
        "block",
        "academic_year",
        "is_current",
    )

    search_fields = (
        "student__user__email",
        "student__user__name",
        "room_number",
    )

    def student_email(self, obj):
        return obj.student.user.email

    student_email.short_description = "Student Email"