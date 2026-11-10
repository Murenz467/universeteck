from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from .models import get_profile


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=60, label="Your name")
    phone = forms.CharField(max_length=30, required=False, label="Phone (optional)")
    company = forms.CharField(max_length=120, required=False, label="Company (optional)")

    class Meta:
        model = get_user_model()
        fields = ("username", "first_name", "email")

    def clean_email(self):
        e = self.cleaned_data["email"].lower()
        if get_user_model().objects.filter(email__iexact=e).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return e

    def save(self, commit=True):
        user = super().save(commit)
        if commit:
            p = get_profile(user)
            p.phone, p.company = self.cleaned_data.get("phone", ""), self.cleaned_data.get("company", "")
            p.save()
        return user


class ProfileForm(forms.Form):
    first_name = forms.CharField(max_length=60, label="Your name")
    last_name = forms.CharField(max_length=60, required=False, label="Surname")
    email = forms.EmailField()
    phone = forms.CharField(max_length=30, required=False)
    company = forms.CharField(max_length=120, required=False)
    email_notifications = forms.BooleanField(required=False, label="Email me about my projects, contracts and invoices")

    def __init__(self, *a, user=None, **kw):
        self.user = user
        p = get_profile(user)
        kw.setdefault("initial", dict(first_name=user.first_name, last_name=user.last_name, email=user.email,
                                      phone=p.phone, company=p.company, email_notifications=p.email_notifications))
        super().__init__(*a, **kw)

    def clean_email(self):
        e = self.cleaned_data["email"].lower()
        if get_user_model().objects.filter(email__iexact=e).exclude(pk=self.user.pk).exists():
            raise forms.ValidationError("Another account already uses this email.")
        return e

    def save(self):
        d, u = self.cleaned_data, self.user
        u.first_name, u.last_name, u.email = d["first_name"], d["last_name"], d["email"]
        u.save()
        p = get_profile(u)
        p.phone, p.company, p.email_notifications = d["phone"], d["company"], d["email_notifications"]
        p.save()
        return u
