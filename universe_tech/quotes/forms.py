from django import forms
from services.models import Service
from .models import QuoteRequest

class QuoteForm(forms.ModelForm):
    services = forms.ModelMultipleChoiceField(
        queryset=Service.objects.filter(is_active=True),
        widget=forms.CheckboxSelectMultiple, required=False, label="Services you need")

    website = forms.CharField(required=False, widget=forms.TextInput(attrs={"tabindex": "-1", "autocomplete": "off"}))  # honeypot

    class Meta:
        model = QuoteRequest
        fields = ["name", "email", "phone", "company", "services", "budget", "details"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "Full name", "autocomplete": "name"}),
            "email": forms.EmailInput(attrs={"placeholder": "you@example.com", "autocomplete": "email"}),
            "phone": forms.TextInput(attrs={"placeholder": "+250 7XX XXX XXX", "autocomplete": "tel"}),
            "company": forms.TextInput(attrs={"placeholder": "Company or organization (optional)", "autocomplete": "organization"}),
            "details": forms.Textarea(attrs={"rows": 5, "placeholder": "What would you like us to build or design? Add goals, features and any deadline."}),
        }
