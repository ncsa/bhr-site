from django.contrib import admin

# Register your models here.
from foo.models import WhitelistEntry, BlockEntry

admin.site.register(WhitelistEntry)
admin.site.register(BlockEntry)
