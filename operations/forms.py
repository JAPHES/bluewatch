from django import forms
from .models import CleanupAssignment

class AssignmentForm(forms.ModelForm):
    class Meta:
        model=CleanupAssignment
        fields=["report","assigned_team","priority","scheduled_cleanup_date","instructions"]
        widgets={"scheduled_cleanup_date":forms.DateInput(attrs={"type":"date"}),"instructions":forms.Textarea(attrs={"rows":3})}
    def __init__(self,*args,user=None,**kwargs):
        super().__init__(*args,**kwargs)
        if user and user.county_id and not user.is_superuser:
            self.fields["report"].queryset=self.fields["report"].queryset.filter(county=user.county,verification_status="verified",is_archived=False)
            self.fields["assigned_team"].queryset=self.fields["assigned_team"].queryset.filter(county=user.county,is_active=True)
        for field in self.fields.values(): field.widget.attrs["class"]="form-control"

class AssignmentUpdateForm(forms.ModelForm):
    class Meta:
        model=CleanupAssignment
        fields=["assignment_status","start_time","completion_time","estimated_waste_collected_kg","disposal_destination","waste_diverted_for_recycling_kg","before_photo","after_photo","completion_notes"]
        widgets={"start_time":forms.DateTimeInput(attrs={"type":"datetime-local"}),"completion_time":forms.DateTimeInput(attrs={"type":"datetime-local"}),"completion_notes":forms.Textarea(attrs={"rows":3})}
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        for field in self.fields.values(): field.widget.attrs["class"]="form-control"
    def clean(self):
        data=super().clean()
        if data.get("assignment_status")==CleanupAssignment.Status.SUBMITTED:
            for field in ["after_photo","estimated_waste_collected_kg","disposal_destination","completion_notes"]:
                if not data.get(field) and not getattr(self.instance,field,None): self.add_error(field,"Required when submitting cleanup evidence.")
        return data
