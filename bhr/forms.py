from django import forms
from django.forms import ModelForm
from bhr.models import is_whitelisted

class BlockForm(ModelForm):

    def clean(self):
        cleaned_data = super(BlockForm, self).clean()
        cidr = self.cleaned_data.get('cidr')
        skip_whitelist = self.cleaned_data.get('skip_whitelist')
        if cidr and not skip_whitelist:
            item = is_whitelisted(cidr)
            if item:
                raise forms.ValidationError("whitelisted: %s: %s" % (item.who, item.why))
        return cleaned_data
