from django.conf import settings
from django.views.generic import View, FormView, TemplateView, DetailView
from django.core.urlresolvers import reverse
from django.shortcuts import render, redirect
from django.http import HttpResponse

from bhr.models import WhitelistEntry, Block, BlockEntry, BHRDB, filter_local_networks
from bhr.forms import AddBlockForm, QueryBlockForm, UnblockForm

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
import datetime

from django.db import transaction



class IndexView(TemplateView):
    template_name = "bhr/index.html"

    def get_context_data(self, **kwargs):
        context = super(IndexView, self).get_context_data(**kwargs)
        context['show_limited'] = settings.BHR.get('unauthenticated_limited_query', False)
        return context


class AddView(FormView):
    template_name = "bhr/add.html"
    form_class = AddBlockForm

    def form_valid(self, form):
        block_request = form.cleaned_data
        block_request['cidr'] = str(block_request['cidr'])
        BHRDB().add_block(who=self.request.user, source='web', **block_request)
        return redirect(reverse("query") + "?query=" +  block_request["cidr"])

class QueryView(View):
    result_template_name = 'bhr/query_result.html'

    def get(self, request):
        if self.request.GET:
            form = QueryBlockForm(self.request.GET)
        else:
            form = QueryBlockForm()

        if not form.is_valid():
            return render(self.request, "bhr/query.html", {"form": form})

        query = form.cleaned_data['query']
        blocks = BHRDB().get_history(query).prefetch_related("blockentry_set")
        return render(self.request, self.result_template_name, {"query": query, "form": form, "blocks": blocks})

class QueryViewLimited(QueryView):
    result_template_name = 'bhr/query_result_limited.html'

class UnblockView(View):
    def post(self, request):
        query = self.request.POST.get("query")
        block_ids = self.request.POST.getlist("block_id")
        blocks = Block.objects.filter(id__in=block_ids).all()
        block_str = " ".join(block_ids)
        form = UnblockForm(initial={"block_ids": block_str, "query": query})
        return render(self.request, "bhr/unblock.html", {"form": form, "blocks": blocks})

class DoUnblockView(FormView):
    template_name = "bhr/unblock.html"
    form_class = UnblockForm

    def get_context_data(self, **kwargs):
        context = super(DoUnblockView, self).get_context_data(**kwargs)

        block_ids = self.request.POST.get("block_ids").split()
        blocks = Block.objects.filter(id__in=block_ids).all()
        context["blocks"] = blocks
        return context

    def form_valid(self, form):
        query = form.cleaned_data['query']
        block_ids = form.cleaned_data['block_ids'].split()
        why = form.cleaned_data['why']

        block_ids = map(int, block_ids)
        blocks = Block.objects.filter(id__in=block_ids).all()
        for b in blocks:
            b.unblock_now(self.request.user, why)

        if query and query != "list":
            return redirect(reverse("query") + "?query=" + query)
        else:
            return redirect(reverse("list"))

class StatsView(TemplateView):
    template_name = "bhr/stats.html"
    def get_context_data(self, *args):
        db = BHRDB()
        return {
            'stats': db.stats(),
            'source_stats': db.source_stats(),
        }

def query_to_blocklist(q):
    return q.values('id', 'cidr','who__username','source','why', 'added', 'unblock_at')

class ListView(TemplateView):
    template_name = "bhr/list.html"
    def get_context_data(self, *args):
        all_blocks = BHRDB().expected()
        manual_blocks = all_blocks.filter(Q(source="web") | Q(source="cli"))
        local_blocks = filter_local_networks(all_blocks)
        auto_blocks = all_blocks.filter(~Q(source="web") | Q(source="cli")).order_by("-added")[:50]
        return {
            'manual_blocks': query_to_blocklist(manual_blocks),
            'local_blocks': query_to_blocklist(local_blocks),
            'auto_blocks': query_to_blocklist(auto_blocks),
            'query': 'list',
        }

class ListViewLimited(TemplateView):
    template_name = "bhr/list_limited.html"
    def get_context_data(self, *args):
        all_blocks = BHRDB().expected()
        manual_blocks = all_blocks.filter(Q(source="web") | Q(source="cli"))
        local_blocks = filter_local_networks(all_blocks)
        return {
            'manual_blocks': query_to_blocklist(manual_blocks),
            'local_blocks': query_to_blocklist(local_blocks),
        }


class SourceListView(TemplateView):
    template_name = "bhr/sourcelist.html"
    def get_context_data(self, source, *args):
        all_blocks = BHRDB().expected()
        blocks = all_blocks.filter(source=source).order_by("-added")[:500]
        return {
            'source': source,
            'blocks': query_to_blocklist(blocks),
        }

def login(request):
    '''Provides a authentication method agnostic login view.

    This gives us something to point to in the templates without requiring us
    to know exactly which authentication method is being used.
    '''

    return redirect(settings.LOGIN_URL)
