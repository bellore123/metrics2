from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

from .models import User


class EmailOrPhoneBackend(ModelBackend):

    def authenticate(
        self,
        request,
        username=None,
        password=None,
        **kwargs
    ):
        identifier = (
            username
            or kwargs.get("email")
            or kwargs.get("phone")
        )

        if not identifier or not password:
            return None

        identifier = identifier.strip().lower()

        try:
            user = User.objects.get(
                Q(email__iexact=identifier)
                | Q(phone=identifier)
            )

        except User.DoesNotExist:
            return None

        except User.MultipleObjectsReturned:
            return None

        if (
            user.check_password(password)
            and self.user_can_authenticate(user)
        ):
            return user

        return None