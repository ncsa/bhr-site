from rest_framework import viewsets
from bhr.models import WhitelistEntry, Block, BlockEntry, BHRDB
from bhr.serializers import (WhitelistEntrySerializer,
    BlockSerializer, BlockBriefSerializer, BlockQueueSerializer,
    BlockEntrySerializer, UnBlockEntrySerializer,
    SetBlockedSerializer,
    BlockRequestSerializer,
)
from rest_framework import status
from rest_framework import generics
from rest_framework.decorators import api_view
from rest_framework.decorators import detail_route, list_route
from rest_framework.settings import api_settings
from rest_framework_csv.renderers import CSVRenderer

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
import datetime

from django.db import transaction

class WhitelistViewSet(viewsets.ModelViewSet):
    queryset = WhitelistEntry.objects.all()
    serializer_class = WhitelistEntrySerializer

    def pre_save(self, obj):
        obj.who = self.request.user
        return super(WhitelistViewSet, self).pre_save(obj)

class BlockEntryViewset(viewsets.ModelViewSet):
    queryset = BlockEntry.objects.all()
    serializer_class = BlockEntrySerializer

    @detail_route(methods=['post'])
    def set_unblocked(self, request, pk=None):
        entry = self.get_object()
        entry.set_unblocked()
        entry.save()
        return Response({'status': 'ok'})

class BlockViewset(viewsets.ModelViewSet):
    queryset = Block.objects.all()
    serializer_class = BlockSerializer

    def pre_save(self, obj):
        """Force who to the current user on save"""
        obj.who = self.request.user
        return super(BlockViewset, self).pre_save(obj)

    @detail_route(methods=['post'])
    def set_blocked(self, request, pk=None):
        block = self.get_object()
        serializer = SetBlockedSerializer(data=request.DATA)
        if serializer.is_valid():
            ident = serializer.data['ident']
            block.blockentry_set.create(ident=ident)
            return Response({'status': 'ok'})
        else:
            return Response(serializer.errors,
                status=status.HTTP_400_BAD_REQUEST)

class CurrentBlockViewset(viewsets.ReadOnlyModelViewSet):
    serializer_class = BlockSerializer
    def get_queryset(self):
        return Block.current.all().select_related('who')

class CurrentBlockBriefViewset(CurrentBlockViewset):
    renderer_classes = [CSVRenderer] + api_settings.DEFAULT_RENDERER_CLASSES
    serializer_class = BlockBriefSerializer

class ExpectedBlockViewset(viewsets.ReadOnlyModelViewSet):
    serializer_class = BlockBriefSerializer
    def get_queryset(self):
        queryset = Block.expected.all().select_related('who')
        source = self.request.QUERY_PARAMS.get('source', None)
        if source:
            queryset = queryset.filter(source=source)
        return queryset


class PendingBlockViewset(viewsets.ReadOnlyModelViewSet):
    serializer_class = BlockSerializer
    def get_queryset(self):
        return Block.pending.all().select_related('who')

class PendingRemovalBlockViewset(viewsets.ReadOnlyModelViewSet):
    serializer_class = BlockSerializer
    def get_queryset(self):
        return Block.pending_removal.all().select_related('who')

from rest_framework.views import APIView
class BlockHistory(generics.ListAPIView):
    serializer_class = BlockSerializer

    def get_queryset(self):
        cidr = self.kwargs['cidr']
        return Block.objects.filter(cidr=cidr).select_related('who')

class BlockQueue(generics.ListAPIView):
    serializer_class = BlockQueueSerializer

    def get_queryset(self):
        ident = self.kwargs['ident']
        return BHRDB().block_queue(ident, limit=200)

class UnBlockQueue(generics.ListAPIView):
    serializer_class = UnBlockEntrySerializer

    def get_queryset(self):
        ident = self.kwargs['ident']
        return BHRDB().unblock_queue(ident)[:200]

from rest_framework.response import Response

@api_view(["POST"])
def block(request):
    context = {"request": request}
    serializer = BlockRequestSerializer(data=request.DATA)
    if serializer.is_valid():
        b = BHRDB().add_block(who=request.user, **serializer.data)
        return Response(BlockSerializer(b, context=context).data, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class mblock(APIView):
    def post(self, request):
        context = {"request": request}
        serializer = BlockRequestSerializer(data=request.DATA, many=True)
        created = []
        if serializer.is_valid():
            #FIXME: move this into BHRDB directly
            with transaction.atomic():
                for block in serializer.data:
                    b = BHRDB().add_block(who=request.user, **block)
                    created.append(b)
            return Response(BlockSerializer(created, many=True, context=context).data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class set_blocked_multi(APIView):
    def post(self, request, ident):
        ids = request.DATA['ids']
        BHRDB().set_blocked_multi(ident, ids)
        return Response({'status': 'ok'})

class set_unblocked_multi(APIView):
    def post(self, request):
        ids = request.DATA['ids']
        BHRDB().set_unblocked_multi(ids)
        return Response({'status': 'ok'})

@api_view(["GET"])
def stats(request):
    stats = BHRDB().stats()
    return Response(stats)

from bhr.util import respond_csv
@api_view(["GET"])
def bhlist(request):
    resp = []
    blocks = BHRDB().expected().values_list('cidr','who__username','source','why', 'added', 'unblock_at')
    return respond_csv(blocks, ["cidr", "who", "source", "why", "added", "unblock_at"])
