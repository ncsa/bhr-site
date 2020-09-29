from bhr.util import resolve 

from django import template
from django.template.defaultfilters import stringfilter


register = template.Library()


@register.filter(name="resolve")
@stringfilter
def resolve_tag(value):
    ip = value.split("/")[0]
    return resolve(ip)
