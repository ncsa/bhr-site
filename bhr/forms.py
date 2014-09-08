from django import forms
from django.forms import ModelForm
from bhr.models import is_whitelisted

class BlockEntryForm(ModelForm):
    def clean_cidr(self):
        cidr = self.cleaned_data['cidr']
        item = is_whitelisted(cidr)
        if item:
            raise forms.ValidationError("whitelisted: %s: %s" % (item.who, item.why))
