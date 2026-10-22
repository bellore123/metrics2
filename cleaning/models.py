from django.db import models

from students.models import StudentProfile, HostelAllocation
from cleaners.models import CleanerProfile
from wardens.models import WardenProfile


ACTIVE_STATUSES = [
    "pending",
    "approved",
    "assigned",
    "scheduled",
    "in_progress",
]


class CleaningRequest(models.Model):

    # ─────────────────────────────────────────────
    # CHOICES
    # ─────────────────────────────────────────────

    TIME_SLOT_CHOICES = [
        ("09:00-10:00", "9:00 AM - 10:00 AM"),
        ("10:00-11:00", "10:00 AM - 11:00 AM"),
        ("14:00-15:00", "2:00 PM - 3:00 PM"),
        ("16:00-17:00", "4:00 PM - 5:00 PM"),
        ("18:00-19:00", "6:00 PM - 7:00 PM"),
    ]

    CLEANING_TYPE_CHOICES = [
        ("room_cleaning", "Room Cleaning"),
        ("sweeping", "Sweeping"),
        ("mopping", "Mopping"),
        ("dusting", "Dusting"),
        ("full", "Full Room Cleaning"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("assigned", "Assigned"),
        ("scheduled", "Scheduled"),
        ("in_progress", "In Progress"),
        ("completed", "Completed"),
        ("confirmed", "Confirmed by Student"),
        ("not_cleaned", "Not Cleaned"),
        ("cancelled", "Cancelled"),
        ("rejected", "Rejected"),
    ]

    # ─────────────────────────────────────────────
    # RELATIONS
    # ─────────────────────────────────────────────

    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="cleaning_requests",
    )

    room = models.ForeignKey(
        "students.Room",
        on_delete=models.PROTECT,
        related_name="cleaning_requests",
        null=True,
        blank=True,
    )

    hostel_allocation = models.ForeignKey(
        HostelAllocation,
        on_delete=models.PROTECT,
        related_name="cleaning_requests",
    )


    # ─────────────────────────────────────────────
    # CLEANING SCHEDULE FIELDS
    # ─────────────────────────────────────────────

    cleaning_date = models.DateField()

    time_slot = models.CharField(
        max_length=20,
        choices=TIME_SLOT_CHOICES,
    )

    cleaning_type = models.CharField(
        max_length=20,
        choices=CLEANING_TYPE_CHOICES,
        default="room_cleaning",
    )

    description = models.TextField(
        blank=True,
        help_text="Description of what needs to be cleaned in the room.",
    )

    remarks = models.TextField(
        blank=True,
        help_text="Any special instructions for the cleaner (optional).",
    )

    # ─────────────────────────────────────────────
    # WARDEN NOTES
    # ─────────────────────────────────────────────

    warden_notes = models.TextField(
        blank=True,
        help_text="Internal notes added by the warden.",
    )

    # ─────────────────────────────────────────────
    # STATUS & ASSIGNMENT
    # ─────────────────────────────────────────────

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )

    assigned_cleaner = models.ForeignKey(
        CleanerProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_requests",
    )

    assigned_by = models.ForeignKey(
        WardenProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_requests",
    )

    completion_date = models.DateField(
        null=True,
        blank=True,
    )

    # ─────────────────────────────────────────────
    # TIMESTAMPS
    # ─────────────────────────────────────────────

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["room"],
                condition=models.Q(status__in=ACTIVE_STATUSES),
                name="unique_active_cleaning_request_per_room",
            )
        ]

    def save(self, *args, **kwargs):
        if not self.room and self.hostel_allocation:
            if not self.hostel_allocation.room:
                from students.models import Room
                room_obj, _ = Room.objects.get_or_create(
                    hostel_name=self.hostel_allocation.hostel_name or "VIT Men's Hostel",
                    block=self.hostel_allocation.block,
                    room_number=self.hostel_allocation.room_number.strip().upper(),
                )
                self.hostel_allocation.room = room_obj
                self.hostel_allocation.save(update_fields=["room"])
            self.room = self.hostel_allocation.room
        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"#{self.pk} – "
            f"{self.student.user.email} – "
            f"{self.hostel_allocation.block} "
            f"Room {self.hostel_allocation.room_number}"
        )

    @property
    def is_active(self):
        return self.status in ACTIVE_STATUSES

    @property
    def is_closed(self):
        return self.status not in ACTIVE_STATUSES

    @property
    def get_description(self):
        return self.description.strip() if self.description else (self.remarks.strip() if self.remarks else "Room cleaning requested")



class Feedback(models.Model):

    ROOM_STATUS_CHOICES = [
        ("cleaned", "Room Cleaned"),
        ("not_cleaned", "Room Not Cleaned"),
    ]

    cleaning_request = models.OneToOneField(
        CleaningRequest,
        on_delete=models.CASCADE,
        related_name="feedback",
    )

    room_status = models.CharField(
        max_length=20,
        choices=ROOM_STATUS_CHOICES,
    )

    rating = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
    )

    comments = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback – {self.cleaning_request}"
