from django.contrib import admin

# Register your models here.
from bhr.models import WhitelistEntry, Block, BlockEntry
from bhr.forms import BlockForm

def force_unblock(modeladmin, request, queryset):
    queryset.update(forced_unblock=True)
force_unblock.short_description = "Force Unblock"

class BlockStatusListFilter(admin.SimpleListFilter):
    title = "status"
    parameter_name = "status"

    def lookups(self, request, model_admin):
        return (
            ('current', 'currently blocked'),
        )

    def queryset(self, request, queryset):
        if self.value() == "current":
            return queryset.filter(
                id__in = BlockEntry.objects.distinct('block_id').filter(removed__isnull=True).values_list('block_id', flat=True))


class AutoWho(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        if getattr(obj, 'who', None) is None:
            obj.who = request.user
        obj.save()

class BlockAdmin(AutoWho):
    date_hierarchy = 'added'
    list_filter = ('who__username', 'source', 'flag', BlockStatusListFilter)
    list_display = ('cidr', 'who', 'source')
    actions = [force_unblock]

    form = BlockForm

class WhitelistAdmin(AutoWho):
    date_hierarchy = 'added'
    list_filter = ('who', )
    list_display = ('cidr', 'who', 'why')


admin.site.register(WhitelistEntry, WhitelistAdmin)
admin.site.register(Block, BlockAdmin)
