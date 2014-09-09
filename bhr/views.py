from rest_framework import viewsets
from bhr.models import WhitelistEntry, Block, BHRDB
from bhr.serializers import WhitelistEntrySerializer, BlockSerializer, BlockRequestSerializer, SetBlockedSerializer
from rest_framework import status
from rest_framework import generics
from rest_framework.decorators import api_view
from rest_framework.decorators import detail_route, list_route

from django.db.models import Q
from django.utils import timezone
import datetime

class WhitelistViewSet(viewsets.ModelViewSet):
    queryset = WhitelistEntry.objects.all()
    serializer_class = WhitelistEntrySerializer

    def pre_save(self, obj):
        obj.who = self.request.user
        return super(WhitelistViewSet, self).pre_save(obj)

class BlockViewset(viewsets.ModelViewSet):
    queryset = Block.objects.all()
    serializer_class = BlockSerializer

    def pre_save(self, obj):
        """Force who to the current user on save"""
        obj.who = self.request.user
        return super(BlockSerializer, self).pre_save(obj)

    @detail_route(methods=['post'])
    def set_blocked(self, request, pk=None):
        print 'here!'
        block = self.get_object()
        serializer = SetBlockedSerializer(data=request.DATA)
        if serializer.is_valid():
            ident = serializer.data['ident']
            block.blockentry_set.create(ident=ident)
            return Response({'status': 'ok'})
        else:
            return Response(serializer.errors,
                status=status.HTTP_400_BAD_REQUEST)

class CurrentBlockViewset(viewsets.ModelViewSet):
    queryset = Block.current.all()
    serializer_class = BlockSerializer

class ExpectedBlockViewset(viewsets.ModelViewSet):
    queryset = Block.expected.all()
    serializer_class = BlockSerializer

class PendingBlockViewset(viewsets.ModelViewSet):
    queryset = Block.pending.all()
    serializer_class = BlockSerializer

from rest_framework.views import APIView
class BlockHistory(generics.ListAPIView):
    serializer_class = BlockSerializer

    def get_queryset(self):
        cidr = self.kwargs['cidr']
        return Block.objects.filter(cidr=cidr)

class BlockQueue(generics.ListAPIView):
    serializer_class = BlockSerializer

    def get_queryset(self):
        ident = self.kwargs['ident']
        return BHRDB().block_queue(ident)

from rest_framework.response import Response

@api_view(["POST"])
def block(request):
    context = {"request": request}
    serializer = BlockRequestSerializer(data=request.DATA)
    if serializer.is_valid():
        b = BHRDB().add_block(who=request.user, **serializer.data)
        return Response(BlockSerializer(b, context=context).data)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

