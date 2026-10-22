from datetime import date

from django import forms

from cleaning.models import CleaningRequest
from .models import HostelAllocation


class HostelAllocationForm(forms.ModelForm):
    registration_number = forms.CharField(
        max_length=20,
        required=False,
        widget=forms.TextInput(
            attrs={"class": "form-control", "placeholder": "Example: 21BCE1234"}
        ),
        label="Registration Number"
    )

    class Meta:
        model = HostelAllocation

        fields = [
            "block",
            "room_number",
            "academic_year",
        ]

        widgets = {
            "block": forms.Select(
                attrs={"class": "form-select"}
            ),
            "room_number": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Example: 412"}
            ),
            "academic_year": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Example: 2026-2027"}
            ),
        }

    def clean_room_number(self):
        room_number = self.cleaned_data["room_number"].strip()
        if not room_number:
            raise forms.ValidationError("Room number is required.")
        if len(room_number) > 10:
            raise forms.ValidationError("Enter a valid room number.")
        return room_number.upper()

    def clean_registration_number(self):
        reg = self.cleaned_data.get("registration_number", "").strip().upper()
        return reg

    def clean_academic_year(self):
        academic_year = self.cleaned_data["academic_year"].strip()
        if len(academic_year) != 9:
            raise forms.ValidationError("Use the format 2026-2027.")
        if academic_year[4] != "-":
            raise forms.ValidationError("Use the format 2026-2027.")
        first_year  = academic_year[:4]
        second_year = academic_year[5:]
        if not first_year.isdigit() or not second_year.isdigit():
            raise forms.ValidationError("Enter a valid academic year.")
        if int(second_year) != int(first_year) + 1:
            raise forms.ValidationError("The second year must follow the first year.")
        return academic_year


class CleaningRequestForm(forms.ModelForm):
    """
    Student form for submitting a room-cleaning request.
    Fields: cleaning date, time slot, description.
    """

    class Meta:
        model = CleaningRequest

        fields = [
            "cleaning_date",
            "time_slot",
            "description",
        ]

        widgets = {
            "cleaning_date": forms.DateInput(
                attrs={"type": "date", "class": "form-control"}
            ),
            "time_slot": forms.Select(
                attrs={"class": "form-select"}
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Describe what needs to be cleaned in your room (e.g., sweep and mop the floor, dust the study desk and shelf).",
                }
            ),
        }

    def clean_cleaning_date(self):
        cleaning_date = self.cleaned_data["cleaning_date"]
        if cleaning_date < date.today():
            raise forms.ValidationError("You cannot select a past date.")
        return cleaning_date