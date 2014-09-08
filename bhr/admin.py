from django.contrib import admin

# Register your models here.
from bhr.models import WhitelistEntry, BlockEntry
from bhr.forms import BlockEntryForm

class BlockAdmin(admin.ModelAdmin):
    date_hierarchy = 'added'
    list_filter = ('who__username', 'source', 'flag')
    list_display = ('cidr', 'who', 'source')

    form = BlockEntryForm

class WhitelistAdmin(admin.ModelAdmin):
    date_hierarchy = 'added'
    list_filter = ('who', )
    list_display = ('cidr', 'who', 'why')

    def save_model(self, request, obj, form, change):
        if getattr(obj, 'who', None) is None:
            obj.who = request.user
        obj.save()


admin.site.register(WhitelistEntry, WhitelistAdmin)
admin.site.register(BlockEntry, BlockAdmin)
