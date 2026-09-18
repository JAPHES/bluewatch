from django import forms
from django.utils import timezone
from .models import Report

class PublicReportForm(forms.ModelForm):
    website = forms.CharField(required=False, widget=forms.HiddenInput)
    consent = forms.BooleanField(label="I consent to BlueWatch processing this report for cleanup coordination.")
    truthful = forms.BooleanField(label="I confirm this report is truthful to the best of my knowledge.")
    class Meta:
        model = Report
        fields = ["original_image", "county", "ward", "location_description", "latitude", "longitude", "waste_category", "estimated_size", "proximity_to_water", "description", "date_observed", "reporter_name", "reporter_phone", "reporter_email"]
        widgets = {"date_observed": forms.DateInput(attrs={"type":"date"}), "description": forms.Textarea(attrs={"rows":4}), "latitude": forms.NumberInput(attrs={"step":"0.000001"}), "longitude": forms.NumberInput(attrs={"step":"0.000001"})}
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.HiddenInput): field.widget.attrs["class"] = "form-check-input" if isinstance(field.widget, forms.CheckboxInput) else "form-control"
    def clean_website(self):
        if self.cleaned_data.get("website"): raise forms.ValidationError("Submission rejected.")
        return ""
    def clean_date_observed(self):
        value = self.cleaned_data["date_observed"]
        if value > timezone.localdate(): raise forms.ValidationError("Date observed cannot be in the future.")
        return value
    def clean(self):
        data = super().clean()
        county, ward = data.get("county"), data.get("ward")
        if county and ward and ward.county_id != county.id: self.add_error("ward", "Select a ward in the chosen county.")
        return data

class TrackingForm(forms.Form):
    reference_code = forms.CharField(max_length=20, label="Report reference", widget=forms.TextInput(attrs={"class":"form-control", "placeholder":"BW-2607-ABC123"}))
    def clean_reference_code(self): return self.cleaned_data["reference_code"].strip().upper()

class OfficerReportForm(forms.ModelForm):
    note = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows":3, "class":"form-control"}))
    class Meta:
        model = Report
        fields = ["verification_status", "operational_status", "risk_level", "assigned_officer", "possible_duplicate_of"]
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values(): field.widget.attrs["class"] = "form-control"

