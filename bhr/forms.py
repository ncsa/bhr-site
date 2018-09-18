from django import forms
from django.forms import ModelForm
from bhr.models import is_whitelisted, is_prefixlen_too_small, is_source_blacklisted
from netfields.forms import CidrAddressFormField

def check_whitelist(cleaned_data):
    cidr = cleaned_data.get('cidr')
    source = cleaned_data.get('source')
    skip_whitelist = cleaned_data.get('skip_whitelist')
    if cidr and not skip_whitelist:
        item = is_whitelisted(cidr)
        if item:
            raise forms.ValidationError("whitelisted: %s: %s" % (item.who, item.why))
        if is_prefixlen_too_small(cidr):
            raise forms.ValidationError("Prefix length in %s is too small" % cidr)
        item = is_source_blacklisted(source)
        if item:
            raise forms.ValidationError("Source %s is blacklisted: %s: %s" % (source, item.who, item.why))
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
    (60*60*24*365,  '1 Year'),
    (0,             'Indefinite'),
)

AUTOFOCUS = {'autofocus': True}

class AddBlockForm(forms.Form):
    cidr = CidrAddressFormField(widget=forms.TextInput(attrs=AUTOFOCUS))
    why = forms.CharField(widget=forms.Textarea)
    duration = forms.ChoiceField(choices=DURATION_CHOICES)
    skip_whitelist = forms.BooleanField(required=False)
    extend = forms.BooleanField(label="Extend duration if existing block found",required=False)

    def clean_duration(self):
        d = self.cleaned_data['duration'] = int(self.cleaned_data['duration'])
        return d

    def clean(self):
        cleaned_data = super(AddBlockForm, self).clean()
        check_whitelist(cleaned_data)
        return cleaned_data

class QueryBlockForm(forms.Form):
    query = forms.CharField(max_length=100, label="CIDR or comment string", widget=forms.TextInput(attrs=AUTOFOCUS))

class UnblockForm(forms.Form):
    block_ids = forms.CharField(max_length=1000, widget=forms.HiddenInput())
    query = forms.CharField(max_length=100, widget=forms.HiddenInput(), required=False)
    why = forms.CharField(widget=forms.Textarea(attrs=AUTOFOCUS))

class AddSourceBlacklistForm(ModelForm):
    source = forms.CharField()
    why = forms.CharField(widget=forms.Textarea(attrs=AUTOFOCUS))
    class Meta:
        exclude = ('who',)
