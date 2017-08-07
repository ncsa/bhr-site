from rest_framework import viewsets
from bhr.models import WhitelistEntry, Block, BlockEntry, BHRDB
from bhr.serializers import (WhitelistEntrySerializer,
    BlockSerializer, BlockLimitedSerializer, BlockBriefSerializer, BlockQueueSerializer, 
    UnblockNowSerializer,
    BlockEntrySerializer, UnBlockEntrySerializer,
    SetBlockedSerializer,
    BlockRequestSerializer,
)
from rest_framework import status
from rest_framework import generics
from rest_framework.decorators import api_view
from rest_framework.decorators import detail_route, list_route
from rest_framework.exceptions import PermissionDenied
from rest_framework.settings import api_settings
from rest_framework.permissions import IsAuthenticated, DjangoModelPermissions, BasePermission
from rest_framework_csv.renderers import CSVRenderer
from rest_framework.response import Response

from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.cache import cache_page
import datetime
import time

from django.db import transaction

def make_permission_class(perm):
    class CustomPermission(BasePermission):
        def has_permission(self, request, view):
            return request.user.has_perm(perm)
    return CustomPermission

class WhitelistViewSet(viewsets.ModelViewSet):
    serializer_class = WhitelistEntrySerializer
    permission_classes = [DjangoModelPermissions]
    queryset = WhitelistEntry.objects.all()

    def pre_save(self, obj):
        obj.who = self.request.user
        return super(WhitelistViewSet, self).pre_save(obj)
    
    def perform_create(self, serializer):
        serializer.save(who = self.request.user)

class BlockEntryViewset(viewsets.ModelViewSet):
    serializer_class = BlockEntrySerializer
    permission_classes = [DjangoModelPermissions]
    queryset = BlockEntry.objects.all()

    @detail_route(methods=['post'])
    def set_unblocked(self, request, pk=None):
        entry = self.get_object()
        entry.set_unblocked()
        entry.save()
        return Response({'status': 'ok'})

class BlockViewset(viewsets.ModelViewSet):
    serializer_class = BlockSerializer
    permission_classes = [DjangoModelPermissions]
    queryset = Block.objects.all()

    def pre_save(self, obj):
        """Force who to the current user on save"""
        obj.who = self.request.user
        return super(BlockViewset, self).pre_save(obj)
    
    def perform_create(self, serializer):
        serializer.save(who = self.request.user)

    @detail_route(methods=['post'])
    def set_blocked(self, request, pk=None):
        if not request.user.has_perm('bhr.add_blockentry'):
            raise PermissionDenied()
        block = self.get_object()
        serializer = SetBlockedSerializer(data=request.data)
        if serializer.is_valid():
            ident = serializer.validated_data['ident']
            BHRDB().set_blocked(block, ident)
            return Response({'status': 'ok'})
        else:
            return Response(serializer.errors,
                status=status.HTTP_400_BAD_REQUEST)

class CurrentBlockViewset(viewsets.ReadOnlyModelViewSet):
    serializer_class = BlockSerializer
    permission_classes = [DjangoModelPermissions]
    queryset = Block.objects.none()  # Required for DjangoModelPermissions
    def get_queryset(self):
        return Block.current.all().select_related('who')

class CurrentBlockBriefViewset(CurrentBlockViewset):
    serializer_class = BlockBriefSerializer
    permission_classes = [DjangoModelPermissions]
    queryset = Block.objects.none()  # Required for DjangoModelPermissions
    renderer_classes = [CSVRenderer] + api_settings.DEFAULT_RENDERER_CLASSES

class ExpectedBlockViewset(viewsets.ReadOnlyModelViewSet):
    serializer_class = BlockBriefSerializer
    permission_classes = [DjangoModelPermissions]
    queryset = Block.objects.none()  # Required for DjangoModelPermissions
    def get_queryset(self):
        queryset = Block.expected.all().select_related('who')
        source = self.request.query_params.get('source', None)
        if source:
            queryset = queryset.filter(source=source)
        return queryset


class PendingBlockViewset(viewsets.ReadOnlyModelViewSet):
    serializer_class = BlockSerializer
    permission_classes = [DjangoModelPermissions]
    queryset = Block.objects.none()  # Required for DjangoModelPermissions
    def get_queryset(self):
        return Block.pending.all().select_related('who')

class PendingRemovalBlockViewset(viewsets.ReadOnlyModelViewSet):
    serializer_class = BlockSerializer
    permission_classes = [DjangoModelPermissions]
    queryset = Block.objects.none()  # Required for DjangoModelPermissions
    def get_queryset(self):
        return Block.pending_removal.all().select_related('who')

from rest_framework.views import APIView
class BlockHistory(generics.ListAPIView):
    serializer_class = BlockSerializer
    permission_classes = [DjangoModelPermissions]
    queryset = Block.objects.none()  # Required for DjangoModelPermissions

    def get_queryset(self):
        cidr = self.kwargs['cidr']
        return Block.objects.filter(cidr__in_cidr=cidr).select_related('who')

class BlockHistoryLimited(BlockHistory):
    serializer_class = BlockLimitedSerializer
    permission_classes = []

class BlockQueue(generics.ListAPIView):
    serializer_class = BlockQueueSerializer
    permission_classes = [make_permission_class('bhr.add_blockentry')]

    def get_queryset(self):
        ident = self.kwargs['ident']
        timeout = int(self.request.query_params.get('timeout', 0))
        added_since = self.request.query_params.get('added_since', '2014-09-01')
        if not timeout:
            return BHRDB().block_queue(ident, limit=200, added_since=added_since)

        end = time.time() + timeout
        while time.time() < end:
            blocks = BHRDB().block_queue(ident, limit=200, added_since=added_since)
            if list(blocks):
                return blocks
            time.sleep(1.0)
        return blocks

class UnBlockQueue(generics.ListAPIView):
    serializer_class = UnBlockEntrySerializer
    permission_classes = [make_permission_class('bhr.change_blockentry')]

    def get_queryset(self):
        ident = self.kwargs['ident']
        return BHRDB().unblock_queue(ident)[:200]

class block(APIView):
    permission_classes = [make_permission_class('bhr.add_block')]
    def post(self, request):
        context = {"request": request}
        serializer = BlockRequestSerializer(data=request.data)
        if serializer.is_valid():
            b = BHRDB().add_block(who=request.user, **serializer.validated_data)
            return Response(BlockSerializer(b, context=context).data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class unblock_now(APIView):
    permission_classes = [make_permission_class('bhr.change_block')]
    def post(self, request):
        serializer = UnblockNowSerializer(data=request.data)
        if serializer.is_valid():
            d = serializer.validated_data
            BHRDB().unblock_now(d['cidr'], request.user, d['why'])
            return Response({'status': 'ok'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class mblock(APIView):
    permission_classes = [make_permission_class('bhr.add_block')]
    def post(self, request):
        context = {"request": request}
        serializer = BlockRequestSerializer(data=request.data, many=True)
        created = []
        if serializer.is_valid():
            created = BHRDB().add_block_multi(who=request.user, blocks=serializer.validated_data)
            return Response(BlockSerializer(created, many=True, context=context).data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class set_blocked_multi(APIView):
    permission_classes = [make_permission_class('bhr.add_blockentry')]
    def post(self, request, ident):
        ids = request.data['ids']
        BHRDB().set_blocked_multi(ident, ids)
        return Response({'status': 'ok'})

class set_unblocked_multi(APIView):
    permission_classes = [make_permission_class('bhr.change_blockentry')]
    def post(self, request):
        ids = request.data['ids']
        BHRDB().set_unblocked_multi(ids)
        return Response({'status': 'ok'})

@api_view(["GET"])
def stats(request):
    db = BHRDB()

    stats = db.stats()
    stats['sources'] = db.source_stats()

    return Response(stats)

@api_view(["GET"])
@cache_page(60*5)
def metrics(request):
    """Export metrics in a format that prometheus can understand"""
    db = BHRDB()

    stats = db.stats()
    source_stats = db.source_stats()
    now = int(1000 * time.time())

    out = []
    def add(k, v):
        out.append("bhr_{} {} {}\n".format(k, v, now))

    out.append('''
# HELP bhr_blocked_total total hosts blocked
# TYPE bhr_blocked_total gauge
''')

    add('blocked_total{type="current"}', stats["current"])
    add('blocked_total{type="expected"}', stats["expected"])

    out.append('''
# HELP bhr_pending_total total hosts pending
# TYPE bhr_pending_total gauge
''')
    add('pending_total{type="block"}', stats["block_pending"])
    add('pending_total{type="unblock"}', stats["unblock_pending"])

    out.append('''
# HELP bhr_blocked_total_by_source total hosts blocked by each source
# TYPE bhr_blocked_total_by_source gauge
''')
    for source, count in source_stats.items():
        add('blocked_total_by_source{source="%s"}' % source, count)

    resp = "".join(out)
    return HttpResponse(resp, content_type="text/plain")

@api_view(["GET"])
def source_stats(request):
    db = BHRDB()
    stats = db.source_stats()

    return Response(stats)

from bhr.util import respond_csv
class bhlist(APIView):
    permission_classes = [DjangoModelPermissions]
    queryset = Block.objects.none()  # Required for DjangoModelPermissions
    def get(self, request):
        #TODO: http://www.django-rest-framework.org/api-guide/filtering/ ?
        source = self.request.query_params.get('source', None)
        since = self.request.query_params.get('since', None)
        queryset = BHRDB().expected()
        if source:
            queryset = queryset.filter(source=source)
        if since:
            queryset = queryset.filter(added__gte=since).order_by('added')
        blocks = queryset.values_list('cidr','who__username','source','why', 'added', 'unblock_at')
        return respond_csv(blocks, ["cidr", "who", "source", "why", "added", "unblock_at"])

@api_view(["GET"])
def bhlistpub(request):
    resp = []
    blocks = BHRDB().expected().values_list('cidr', 'added', 'unblock_at')
    return respond_csv(blocks, ["cidr", "added", "unblock_at"])
