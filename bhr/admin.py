from django.contrib import admin

# Register your models here.
from bhr.models import WhitelistEntry, Block
from bhr.forms import BlockForm

class AutoWho(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        if getattr(obj, 'who', None) is None:
            obj.who = request.user
        obj.save()


class BlockAdmin(AutoWho):
    date_hierarchy = 'added'
    list_filter = ('who__username', 'source', 'flag')
    list_display = ('cidr', 'who', 'source')

    form = BlockForm

class WhitelistAdmin(AutoWho):
    date_hierarchy = 'added'
    list_filter = ('who', )
    list_display = ('cidr', 'who', 'why')


admin.site.register(WhitelistEntry, WhitelistAdmin)
admin.site.register(Block, BlockAdmin)
