from django.contrib import admin

# Register your models here.
from bhr.models import WhitelistEntry, BlockEntry

admin.site.register(WhitelistEntry)
admin.site.register(BlockEntry)
