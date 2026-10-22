from django import forms
from django.contrib.auth import authenticate


class EmailOrPhoneLoginForm(forms.Form):

    identifier = forms.CharField(
        label="Email ID or phone number",
        max_length=254,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": (
                    "Enter VIT email, Gmail, or phone number"
                ),
                "autocomplete": "username",
            }
        ),
    )

    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your password",
                "autocomplete": "current-password",
            }
        ),
    )

    def __init__(self, request=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.request = request
        self.user_cache = None

    def clean(self):
        cleaned_data = super().clean()

        identifier = cleaned_data.get("identifier")
        password = cleaned_data.get("password")

        if identifier and password:
            self.user_cache = authenticate(
                request=self.request,
                username=identifier,
                password=password
            )

            if self.user_cache is None:
                raise forms.ValidationError(
                    "Incorrect login ID or password."
                )

            if not self.user_cache.is_active:
                raise forms.ValidationError(
                    "This account is inactive."
                )

        return cleaned_data

    def get_user(self):
        return self.user_cache