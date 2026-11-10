from django import forms
from .models import Ticket

class TicketForm(forms.ModelForm):
    message = forms.CharField(widget=forms.Textarea(attrs={"rows": 6}), label="How can we help?")

    class Meta:
        model = Ticket
        fields = ["subject", "project"]

    def __init__(self, *a, user=None, **kw):
        super().__init__(*a, **kw)
        self.fields["project"].queryset = user.projects.all()
        self.fields["project"].required = False
        self.fields["project"].empty_label = "Not about a specific project"

class ReplyForm(forms.Form):
    body = forms.CharField(widget=forms.Textarea(attrs={"rows": 4}), label="Your reply")
