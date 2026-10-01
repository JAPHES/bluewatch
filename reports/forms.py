from django import forms
from .models import Report, validate_image

class PublicReportForm(forms.Form):
    website = forms.CharField(required=False, widget=forms.HiddenInput)
    original_image = forms.ImageField(validators=[validate_image], label="Photograph")
    reporter_email = forms.EmailField(required=False, label="Email address (optional)")
    latitude = forms.DecimalField(max_digits=9, decimal_places=6, widget=forms.HiddenInput)
    longitude = forms.DecimalField(max_digits=9, decimal_places=6, widget=forms.HiddenInput)
    location_token = forms.CharField(widget=forms.HiddenInput)
    confirmation = forms.BooleanField(label="I confirm this report is truthful and consent to its use for cleanup coordination.")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.HiddenInput): field.widget.attrs["class"] = "form-check-input" if isinstance(field.widget, forms.CheckboxInput) else "form-control"
    def clean_website(self):
        if self.cleaned_data.get("website"): raise forms.ValidationError("Submission rejected.")
        return ""

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

