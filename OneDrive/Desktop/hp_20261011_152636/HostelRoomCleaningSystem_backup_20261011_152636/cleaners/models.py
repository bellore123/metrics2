from django.db import models
from django.conf import settings


class CleanerProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cleaner_profile"
    )

    employee_id = models.CharField(max_length=20, unique=True)
    phone_number = models.CharField(max_length=15, blank=True)
    assigned_block = models.CharField(max_length=20, blank=True)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.user.name} - {self.employee_id}"