from django.conf import settings
from django.db import models


HOSTEL_BLOCK_CHOICES = [
    ("MH A", "MH A - Albert Einstein"),
    ("MH B", "MH B - Swami Vivekananda"),
    (
        "MH B ANNEX",
        "MH B Annex - Swami Vivekananda"
    ),
    ("MH C", "MH C - Rabindranath Tagore"),
    ("MH D", "MH D - Nelson Mandela"),
    (
        "MH D ANNEX",
        "MH D Annex - Nelson Mandela"
    ),
    ("MH E", "MH E - Sir C.V. Raman"),
    ("MH F", "MH F - Ramanujam"),
    ("MH G", "MH G - Socrates"),
    ("MH H", "MH H - John F. Kennedy"),
    ("MH J", "MH J - John F. Kennedy"),
    (
        "MH K",
        "MH K - Dr. Sarvepalli Radhakrishnan"
    ),
    (
        "MH L",
        "MH L - Netaji Subhas Chandra Bose"
    ),
    (
        "MH M",
        "MH M - Quaid-E-Millat Muhammed Ismail"
    ),
    (
        "MH M ANNEX",
        "MH M Annex - Quaid-E-Millat Muhammed Ismail"
    ),
    ("MH N", "MH N - Charles Darwin"),
    (
        "MH N ANNEX",
        "MH N Annex - Charles Darwin"
    ),
    ("MH P", "MH P - Sardar Patel"),
    ("MH Q", "MH Q - Vajpayee Block"),
    (
        "MH R",
        "MH R - M. Karunanidhi"
    ),
    ("MH S", "MH S - Abdul Kalam Block"),
    (
        "MH T",
        "MH T - Jagadish Chandra Bose Block"
    ),
]


class StudentProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="student_profile"
    )

    registration_number = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Student Registration Number (e.g. 21BCE1234)"
    )

    def get_registration_number(self):
        if self.registration_number:
            return self.registration_number.strip().upper()
        if self.user and self.user.email:
            prefix = self.user.email.split("@")[0]
            import re
            m = re.search(r"([0-9]{2}[a-zA-Z]{3}[0-9]{4})", prefix)
            if m:
                return m.group(1).upper()
            return prefix.upper()
        return "N/A"

    def __str__(self):
        reg = f" ({self.get_registration_number()})" if self.registration_number else ""
        return f"{self.user.email}{reg}"


class Room(models.Model):
    hostel_name = models.CharField(
        max_length=100,
        default="VIT Men's Hostel"
    )

    block = models.CharField(
        max_length=20,
        choices=HOSTEL_BLOCK_CHOICES
    )

    room_number = models.CharField(
        max_length=10
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        unique_together = ("hostel_name", "block", "room_number")
        ordering = ["block", "room_number"]

    def __str__(self):
        return f"{self.block} - {self.room_number}"

    @property
    def room_display(self):
        return f"{self.block} – {self.room_number}"

    def get_active_cleaning_request(self):
        from cleaning.models import CleaningRequest, ACTIVE_STATUSES
        return self.cleaning_requests.filter(
            status__in=ACTIVE_STATUSES
        ).order_by("-created_at").first()

    def has_active_cleaning_request(self):
        from cleaning.models import CleaningRequest, ACTIVE_STATUSES
        return self.cleaning_requests.filter(
            status__in=ACTIVE_STATUSES
        ).exists()


class HostelAllocation(models.Model):
    student = models.ForeignKey(
        StudentProfile,
        on_delete=models.CASCADE,
        related_name="allocations"
    )

    room = models.ForeignKey(
        Room,
        on_delete=models.CASCADE,
        related_name="allocations",
        null=True,
        blank=True
    )

    hostel_name = models.CharField(
        max_length=100,
        default="VIT Men's Hostel"
    )

    block = models.CharField(
        max_length=20,
        choices=HOSTEL_BLOCK_CHOICES
    )

    room_number = models.CharField(
        max_length=10
    )

    academic_year = models.CharField(
        max_length=20
    )

    is_current = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = [
            "-is_current",
            "-created_at"
        ]

    def save(self, *args, **kwargs):
        # Auto-link or sync Room
        clean_block = self.block.strip()
        clean_room_no = self.room_number.strip().upper()
        clean_hostel_name = (self.hostel_name or "VIT Men's Hostel").strip()

        room_obj, _ = Room.objects.get_or_create(
            hostel_name=clean_hostel_name,
            block=clean_block,
            room_number=clean_room_no,
        )
        self.room = room_obj
        self.block = clean_block
        self.room_number = clean_room_no
        self.hostel_name = clean_hostel_name

        # When a new current allocation is saved,
        # make all previous allocations inactive.
        if self.is_current:
            HostelAllocation.objects.filter(
                student=self.student,
                is_current=True
            ).exclude(
                pk=self.pk
            ).update(
                is_current=False
            )

        super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.student.user.email} - "
            f"{self.block} - Room {self.room_number}"
        )