from django import forms
from django.forms import ModelForm
from bhr.models import is_whitelisted
from netfields.forms import CidrAddressFormField

def check_whitelistr(cleaned_data):
    cidr = cleaned_data.get('cidr')
    skip_whitelist = cleaned_data.get('skip_whitelist')
    if cidr and not skip_whitelist:
        item = is_whitelisted(cidr)
        if item:
            raise forms.ValidationError("whitelisted: %s: %s" % (item.who, item.why))
    return cleaned_data

class BlockForm(ModelForm):
    def clean(self):
        cleaned_data = super(BlockForm, self).clean()
        check_whitelist(cleaned_data)
        return cleaned_data

DURATION_CHOICES = (
    (300,           '5 minutes'),
    (3600,          '1 Hour'),
    (60*60*24,      '1 Day'),
    (60*60*24*7,    '1 Week'),
    (60*60*24*30,   '1 Month'),
    (60*60*24*30*3, '3 Months'),
)

class AddBlockForm(forms.Form):
    cidr = CidrAddressFormField()
    why = forms.CharField(widget=forms.Textarea)
    duration = forms.ChoiceField(choices=DURATION_CHOICES)
    skip_whitelist = forms.BooleanField(required=False)

    def clean_duration(self):
        d = self.cleaned_data['duration'] = int(self.cleaned_data['duration'])
        return d

    def clean(self):
        cleaned_data = super(AddBlockForm, self).clean()
        check_whitelistr(cleaned_data)
        print cleaned_data
        return cleaned_data

class QueryBlockForm(forms.Form):
    cidr = CidrAddressFormField()
