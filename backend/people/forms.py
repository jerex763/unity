from django import forms

from tenancy.models import Church


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
