import re

from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.core.exceptions import PermissionDenied


STUDENT_DOMAIN = "vitstudent.ac.in"

WARDEN_EMAIL_PATTERN = re.compile(
    r"^cleanstay\.warden\."
    r"(mha|mhb|mhbannex|mhc|mhd|mhdannex|mhe|mhf|mhg|mhh|mhj|mhk|mhl|mhm|mhmannex|mhn|mhnannex|mhp|mhq|mhr|mhs|mht)"
    r"@gmail\.com$"
)


class RoleAwareSocialAccountAdapter(
    DefaultSocialAccountAdapter
):
    """
    Handles Google authentication for students and wardens.

    Student:
        Must use @vitstudent.ac.in

    Development warden:
        Must follow:
        cleanstay.warden.<block>@gmail.com
    """

    def pre_social_login(
        self,
        request,
        sociallogin
    ):
        email = self.get_social_email(
            sociallogin
        )

        if not email:
            raise PermissionDenied(
                "Google did not provide an email address."
            )

        intended_role = request.session.get(
            "google_login_role"
        )

        detected_role = self.detect_role_from_email(
            email
        )

        if detected_role is None:
            raise PermissionDenied(
                "This Google account is not authorised. "
                "Students must use @vitstudent.ac.in. "
                "Wardens must use the CleanStay warden "
                "Gmail format."
            )

        if (
            intended_role
            and intended_role != detected_role
        ):
            raise PermissionDenied(
                f"This account cannot access the "
                f"{intended_role.title()} portal."
            )

        existing_user = sociallogin.user

        if existing_user.pk:
            if (
                existing_user.role
                and existing_user.role != detected_role
            ):
                raise PermissionDenied(
                    "This Google account is already registered "
                    "with another role."
                )

            existing_user.role = detected_role

            if not existing_user.name:
                existing_user.name = self.get_social_name(
                    sociallogin,
                    email
                )

            existing_user.save(
                update_fields=[
                    "role",
                    "name",
                ]
            )

    def populate_user(
        self,
        request,
        sociallogin,
        data
    ):
        user = super().populate_user(
            request,
            sociallogin,
            data
        )

        email = (
            data.get("email")
            or self.get_social_email(
                sociallogin
            )
        ).lower().strip()

        role = self.detect_role_from_email(
            email
        )

        if role is None:
            raise PermissionDenied(
                "This Google account is not authorised."
            )

        intended_role = request.session.get(
            "google_login_role"
        )

        if (
            intended_role
            and intended_role != role
        ):
            raise PermissionDenied(
                f"This account cannot access the "
                f"{intended_role.title()} portal."
            )

        user.email = email
        user.name = (
            data.get("name")
            or self.get_social_name(
                sociallogin,
                email
            )
        )
        user.role = role

        return user

    def save_user(
        self,
        request,
        sociallogin,
        form=None
    ):
        user = super().save_user(
            request,
            sociallogin,
            form
        )

        role = self.detect_role_from_email(
            user.email
        )

        if role is None:
            raise PermissionDenied(
                "This Google account is not authorised."
            )

        user.role = role

        if not user.name:
            user.name = (
                user.email.split("@")[0]
            )

        user.save(
            update_fields=[
                "role",
                "name",
            ]
        )

        request.session.pop(
            "google_login_role",
            None
        )

        return user

    @staticmethod
    def get_social_email(
        sociallogin
    ):
        extra_data = (
            sociallogin.account.extra_data
            or {}
        )

        email = (
            extra_data.get("email")
            or getattr(
                sociallogin.user,
                "email",
                ""
            )
        )

        return email.lower().strip()

    @staticmethod
    def get_social_name(
        sociallogin,
        email
    ):
        extra_data = (
            sociallogin.account.extra_data
            or {}
        )

        return (
            extra_data.get("name")
            or email.split("@")[0]
        ).strip()

    @staticmethod
    def detect_role_from_email(
        email
    ):
        email = email.lower().strip()

        if email.endswith(
            f"@{STUDENT_DOMAIN}"
        ):
            return "student"

        if WARDEN_EMAIL_PATTERN.fullmatch(
            email
        ):
            return "warden"

        return None