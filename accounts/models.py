import re

from django.conf import settings
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.core.exceptions import ValidationError
from django.db import models


# =========================================================
# EMAIL AND PHONE VALIDATION
# =========================================================

STUDENT_EMAIL_PATTERN = (
    r"^[a-zA-Z][a-zA-Z0-9._-]*[0-9]{4}"
    r"@vitstudent\.ac\.in$"
)

PHONE_PATTERN = r"^[6-9][0-9]{9}$"


# =========================================================
# OFFICIAL WARDEN EMAILS
# Used later when real VIT accounts are available
# =========================================================

OFFICIAL_WARDEN_EMAIL_TO_BLOCK = {
    "mhablock@vit.ac.in": "MH A",
    "mhbblock@vit.ac.in": "MH B",
    "mhbannex@vit.ac.in": "MH B ANNEX",
    "mhcblock@vit.ac.in": "MH C",
    "mhdblock@vit.ac.in": "MH D",
    "mhdannex@vit.ac.in": "MH D ANNEX",
    "mheblock@vit.ac.in": "MH E",
    "mhfblock@vit.ac.in": "MH F",
    "mhgblock@vit.ac.in": "MH G",
    "mhhblock@vit.ac.in": "MH H",
    "mhjblock@vit.ac.in": "MH J",
    "mhkblock@vit.ac.in": "MH K",
    "mhlblock@vit.ac.in": "MH L",
    "mhmblock@vit.ac.in": "MH M",
    "mhmannex@vit.ac.in": "MH M ANNEX",
    "mhnblock@vit.ac.in": "MH N",
    "mhnannex@vit.ac.in": "MH N ANNEX",
    "mhpblock@vit.ac.in": "MH P",
    "mhqblock@vit.ac.in": "MH Q",
    "mhrblock@vit.ac.in": "MH R",
    "mhsblock@vit.ac.in": "MH S",
    "mhtblock@vit.ac.in": "MH T",
}


# =========================================================
# DEVELOPMENT WARDEN GOOGLE ACCOUNTS
# Allowed only while DEBUG=True
# =========================================================

TEST_WARDEN_EMAIL_TO_BLOCK = {
    "cleanstay.warden.mha@gmail.com": "MH A",
    "cleanstay.warden.mhb@gmail.com": "MH B",
    "cleanstay.warden.mhbannex@gmail.com": "MH B ANNEX",
    "cleanstay.warden.mhc@gmail.com": "MH C",
    "cleanstay.warden.mhd@gmail.com": "MH D",
    "cleanstay.warden.mhdannex@gmail.com": "MH D ANNEX",
    "cleanstay.warden.mhe@gmail.com": "MH E",
    "cleanstay.warden.mhf@gmail.com": "MH F",
    "cleanstay.warden.mhg@gmail.com": "MH G",
    "cleanstay.warden.mhh@gmail.com": "MH H",
    "cleanstay.warden.mhj@gmail.com": "MH J",
    "cleanstay.warden.mhk@gmail.com": "MH K",
    "cleanstay.warden.mhl@gmail.com": "MH L",
    "cleanstay.warden.mhm@gmail.com": "MH M",
    "cleanstay.warden.mhmannex@gmail.com": "MH M ANNEX",
    "cleanstay.warden.mhn@gmail.com": "MH N",
    "cleanstay.warden.mhnannex@gmail.com": "MH N ANNEX",
    "cleanstay.warden.mhp@gmail.com": "MH P",
    "cleanstay.warden.mhq@gmail.com": "MH Q",
    "cleanstay.warden.mhr@gmail.com": "MH R",
    "cleanstay.warden.mhs@gmail.com": "MH S",
    "cleanstay.warden.mht@gmail.com": "MH T",
}


def get_warden_email_to_block():
    """
    Returns the allowed warden-account mapping.

    Development:
        Official VIT accounts and CleanStay test Gmail accounts.

    Production:
        Only official VIT accounts.
    """

    email_mapping = OFFICIAL_WARDEN_EMAIL_TO_BLOCK.copy()

    if settings.DEBUG:
        email_mapping.update(TEST_WARDEN_EMAIL_TO_BLOCK)

    return email_mapping


# =========================================================
# CUSTOM USER MANAGER
# =========================================================

class UserManager(BaseUserManager):

    def create_user(
        self,
        email=None,
        name=None,
        password=None,
        phone=None,
        **extra_fields
    ):
        if not name:
            raise ValueError("Name is required.")

        role = extra_fields.get("role")

        if email:
            email = self.normalize_email(email).lower().strip()

        if phone:
            phone = phone.strip()

        if role != "cleaner" and not email:
            raise ValueError(
                "Email is required for students, wardens, and admins."
            )

        if role == "cleaner" and not email and not phone:
            raise ValueError(
                "A cleaner must have either an email or phone number."
            )

        user = self.model(
            email=email or None,
            phone=phone or None,
            name=name,
            **extra_fields
        )

        user.set_password(password)

        user.full_clean()

        user.save(using=self._db)

        return user

    def create_superuser(
        self,
        email,
        name,
        password=None,
        **extra_fields
    ):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("role", "admin")

        if extra_fields.get("is_staff") is not True:
            raise ValueError(
                "Superuser must have is_staff=True."
            )

        if extra_fields.get("is_superuser") is not True:
            raise ValueError(
                "Superuser must have is_superuser=True."
            )

        return self.create_user(
            email=email,
            name=name,
            password=password,
            **extra_fields
        )


# =========================================================
# CUSTOM USER MODEL
# =========================================================

class User(AbstractUser):

    username = None

    ROLE_CHOICES = [
        ("student", "Student"),
        ("warden", "Warden"),
        ("cleaner", "Cleaner"),
        ("admin", "Admin"),
    ]

    name = models.CharField(
        max_length=100
    )

    email = models.EmailField(
        unique=True,
        blank=True,
        null=True
    )

    phone = models.CharField(
        max_length=10,
        unique=True,
        blank=True,
        null=True
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES
    )

    USERNAME_FIELD = "email"

    REQUIRED_FIELDS = ["name"]

    objects = UserManager()

    # =====================================================
    # GENERAL VALIDATION
    # =====================================================

    def clean(self):
        super().clean()

        if self.email:
            self.email = self.email.strip().lower()
        else:
            self.email = None

        if self.phone:
            self.phone = self.phone.strip()
        else:
            self.phone = None

        if self.role == "student":
            self.validate_student()

        elif self.role == "warden":
            self.validate_warden()

        elif self.role == "cleaner":
            self.validate_cleaner()

        elif self.role == "admin":
            self.validate_admin()

    # =====================================================
    # STUDENT VALIDATION
    # =====================================================

    def validate_student(self):
        if not self.email:
            raise ValidationError(
                {
                    "email": (
                        "A VIT student email is required."
                    )
                }
            )

        if not re.fullmatch(
            STUDENT_EMAIL_PATTERN,
            self.email
        ):
            raise ValidationError(
                {
                    "email": (
                        "Student email must end with a 4-digit year "
                        "and @vitstudent.ac.in. Example: "
                        "inbarasan.2023@vitstudent.ac.in"
                    )
                }
            )

        if self.phone:
            raise ValidationError(
                {
                    "phone": (
                        "Students must log in using their "
                        "VIT student email."
                    )
                }
            )

    # =====================================================
    # WARDEN VALIDATION
    # =====================================================

    def validate_warden(self):
        if not self.email:
            raise ValidationError(
                {
                    "email": (
                        "A warden Google account is required."
                    )
                }
            )

        allowed_warden_accounts = get_warden_email_to_block()

        if self.email not in allowed_warden_accounts:
            if settings.DEBUG:
                error_message = (
                    "Use an approved CleanStay warden Gmail account. "
                    "Example: cleanstay.warden.mha@gmail.com"
                )
            else:
                error_message = (
                    "Use an approved official VIT warden account."
                )

            raise ValidationError(
                {
                    "email": error_message
                }
            )

        if self.phone:
            raise ValidationError(
                {
                    "phone": (
                        "Wardens must log in using Google authentication."
                    )
                }
            )

    # =====================================================
    # CLEANER VALIDATION
    # =====================================================

    def validate_cleaner(self):
        if not self.email and not self.phone:
            raise ValidationError(
                "A cleaner must have either a Gmail address "
                "or phone number."
            )

        if self.phone and not re.fullmatch(
            PHONE_PATTERN,
            self.phone
        ):
            raise ValidationError(
                {
                    "phone": (
                        "Enter a valid 10-digit Indian mobile number."
                    )
                }
            )

    # =====================================================
    # ADMIN VALIDATION
    # =====================================================

    def validate_admin(self):
        if not self.email:
            raise ValidationError(
                {
                    "email": "Admin email is required."
                }
            )

    # =====================================================
    # WARDEN BLOCK
    # =====================================================

    @property
    def warden_block(self):
        """
        Returns the hostel block assigned through the warden email.

        Example:
            cleanstay.warden.mha@gmail.com -> MH A
        """

        if self.role != "warden" or not self.email:
            return None

        allowed_warden_accounts = get_warden_email_to_block()

        return allowed_warden_accounts.get(
            self.email.lower().strip()
        )

    # =====================================================
    # SAVE
    # =====================================================

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        else:
            self.email = None

        if self.phone:
            self.phone = self.phone.strip()
        else:
            self.phone = None

        super().save(*args, **kwargs)

    def __str__(self):
        return self.email or self.phone or self.name