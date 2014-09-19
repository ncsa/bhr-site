from django.views.generic import View, FormView, TemplateView, DetailView
from django.shortcuts import render
from django.http import HttpResponse

from bhr.models import WhitelistEntry, Block, BlockEntry, BHRDB
from bhr.forms import AddBlockForm, QueryBlockForm

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
import datetime

from django.db import transaction



class IndexView(TemplateView):
    template_name = "bhr/index.html"

class AddView(FormView):
    template_name = "bhr/add.html"
    form_class = AddBlockForm
    success_url = '/bhr'

    def form_valid(self, form):
        block_request = form.cleaned_data
        block_request['cidr'] = str(block_request['cidr'])
        BHRDB().add_block(who=self.request.user, source='web', **block_request)
        return super(AddView, self).form_valid(form)

class QueryView(View):
    def get(self, request):
        form = QueryBlockForm(self.request.GET)
        if not form.is_valid():
            return render(self.request, "bhr/query.html", {"form": form})

        blocks = BHRDB().get_history(form.cleaned_data['cidr']).prefetch_related("blockentry_set")
        return render(self.request, "bhr/query_result.html", {"form": form, "blocks": blocks})

class StatsView(TemplateView):
    template_name = "bhr/stats.html"
    def get_context_data(self, *args):
        return {'stats': BHRDB().stats()}
