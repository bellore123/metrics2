from django import forms

from cleaners.models import CleanerProfile


class AssignCleanerForm(forms.Form):
    cleaner = forms.ModelChoiceField(
        queryset=CleanerProfile.objects.none(),
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, assigned_block="", **kwargs):
        super().__init__(*args, **kwargs)
        queryset = CleanerProfile.objects.filter(
            is_available=True
        ).select_related("user")
        if assigned_block:
            queryset = queryset.filter(assigned_block=assigned_block)
        self.fields["cleaner"].queryset = queryset
