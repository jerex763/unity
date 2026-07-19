from datetime import date

from django import forms

from tenancy.models import Church

from .models import Person


class PersonAdminForm(forms.ModelForm):
    date_of_birth = forms.DateField(
        label="Date of birth",
        required=False,
        widget=forms.SelectDateWidget(
            empty_label=("Year", "Month", "Day"),
            years=range(date.today().year, date.today().year - 121, -1),
        ),
    )
    interests = forms.CharField(
        help_text=(
            "Optional. Separate interests with commas, for example: Music, Hiking."
        ),
        required=False,
        widget=forms.TextInput(attrs={"placeholder": "Music, Hiking"}),
    )

    class Meta:
        model = Person
        fields = (
            "church",
            "full_name",
            "preferred_name",
            "gender",
            "date_of_birth",
            "email",
            "phone",
            "has_whatsapp",
            "photo_url",
            "home_country",
            "suburb",
            "occupation",
            "university",
            "course",
            "interests",
            "household",
            "membership_status",
            "discipleship_stage",
            "faith_background",
            "invited_by",
            "notes",
        )

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        if self.instance and isinstance(self.instance.interests, list):
            self.initial["interests"] = ", ".join(self.instance.interests)
        for field in self.fields.values():
            if field.required and field.label:
                field.label = f"{field.label} (required)"

    def clean_interests(self) -> list[str]:
        raw_value = self.cleaned_data["interests"]
        values = (value.strip() for value in raw_value.split(","))
        return list(dict.fromkeys(value for value in values if value))


class PersonCsvImportForm(forms.Form):
    church = forms.ModelChoiceField(queryset=Church.objects.order_by("name"))
    csv_file = forms.FileField(
        help_text="UTF-8 CSV, up to 5 MB. Use semicolons between interests."
    )
    dry_run = forms.BooleanField(
        required=False,
        initial=True,
        help_text="Validate and preview counts without saving.",
    )

    def clean_csv_file(self):
        upload = self.cleaned_data["csv_file"]
        if upload.size > 5 * 1024 * 1024:
            raise forms.ValidationError("CSV files must be 5 MB or smaller.")
        if not upload.name.lower().endswith(".csv"):
            raise forms.ValidationError("Choose a .csv file.")
        return upload
