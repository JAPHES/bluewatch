import json
from django import forms
from django.utils import timezone
from locations.models import Ward
from reports.models import Report, WasteCategory, validate_image
from .models import AreaOfInterest, ObservationCandidate, ObservationSurvey, validate_polygon


class AreaForm(forms.ModelForm):
    boundary_text = forms.CharField(widget=forms.HiddenInput)

    class Meta:
        model = AreaOfInterest
        fields = ["name", "county", "ward", "description"]
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user and user.county_id and not user.is_superuser:
            self.fields["county"].queryset = self.fields["county"].queryset.filter(pk=user.county_id)
            self.fields["county"].initial = user.county
            self.fields["county"].disabled = True
            self.fields["ward"].queryset = Ward.objects.filter(county=user.county, is_active=True)
        for field in self.fields.values():
            if not isinstance(field.widget, forms.HiddenInput):
                field.widget.attrs["class"] = "form-control"

    def clean_boundary_text(self):
        try:
            boundary = json.loads(self.cleaned_data["boundary_text"])
        except (TypeError, ValueError):
            raise forms.ValidationError("Draw and save one valid area on the map.")
        validate_polygon(boundary)
        return boundary

    def clean(self):
        data = super().clean()
        if data.get("county") and data.get("ward") and data["county"].pk != data["ward"].county_id:
            self.add_error("ward", "Select a ward in the chosen county.")
        return data

    def save(self, commit=True):
        item = super().save(commit=False)
        item.boundary = self.cleaned_data["boundary_text"]
        if commit: item.save()
        return item


class SurveyForm(forms.ModelForm):
    class Meta:
        model = ObservationSurvey
        fields = ["title", "imagery_source", "imagery_capture_date", "imagery_reference", "method"]
        widgets = {"imagery_capture_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values(): field.widget.attrs["class"] = "form-control"

    def clean_imagery_capture_date(self):
        value = self.cleaned_data.get("imagery_capture_date")
        if value and value > timezone.localdate():
            raise forms.ValidationError("The imagery date cannot be in the future.")
        return value

    def clean_method(self):
        method = self.cleaned_data["method"]
        if method == ObservationSurvey.Method.EXTERNAL:
            raise forms.ValidationError("No automated provider is configured. Use human visual review for now.")
        return method


class CandidateForm(forms.ModelForm):
    class Meta:
        model = ObservationCandidate
        fields = ["latitude", "longitude", "suggested_category", "description"]
        widgets = {"latitude": forms.HiddenInput(), "longitude": forms.HiddenInput(), "description": forms.Textarea(attrs={"rows": 3, "class": "form-control"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["suggested_category"].widget.attrs["class"] = "form-control"


class CandidateReviewForm(forms.ModelForm):
    class Meta:
        model = ObservationCandidate
        fields = ["review_status", "suggested_category", "review_note"]
        widgets = {"review_note": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["review_status"].choices = [
            choice for choice in self.fields["review_status"].choices
            if choice[0] in {ObservationCandidate.ReviewStatus.SUSPECTED, ObservationCandidate.ReviewStatus.DISMISSED}
        ]
        for field in self.fields.values(): field.widget.attrs["class"] = "form-control"

    def clean_review_note(self):
        note = self.cleaned_data["review_note"].strip()
        if not note: raise forms.ValidationError("Record the reason for the review decision.")
        return note


class CandidateReportForm(forms.Form):
    ward = forms.ModelChoiceField(queryset=Ward.objects.none())
    waste_category = forms.ModelChoiceField(queryset=WasteCategory.objects.filter(is_active=True))
    original_image = forms.ImageField(validators=[validate_image], help_text="Upload a licensed imagery extract or field-verification photograph.")
    location_description = forms.CharField(max_length=255)
    estimated_size = forms.ChoiceField(choices=Report.Size.choices)
    proximity_to_water = forms.ChoiceField(choices=Report.Water.choices)
    description = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}))
    date_observed = forms.DateField(widget=forms.DateInput(attrs={"type": "date"}), initial=timezone.localdate)

    def __init__(self, *args, county, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["ward"].queryset = Ward.objects.filter(county=county, is_active=True)
        for field in self.fields.values(): field.widget.attrs["class"] = "form-control"

    def clean_date_observed(self):
        value = self.cleaned_data["date_observed"]
        if value > timezone.localdate(): raise forms.ValidationError("The observation date cannot be in the future.")
        return value
