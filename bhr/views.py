from rest_framework import viewsets
from bhr.models import WhitelistEntry, BlockEntry, BlockManager
from bhr.serializers import WhitelistEntrySerializer, BlockEntrySerializer, BlockRequestSerializer
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

class BlockEntryViewset(viewsets.ModelViewSet):
    queryset = BlockEntry.objects.all()
    serializer_class = BlockEntrySerializer

    def pre_save(self, obj):
        """Force who to the current user on save"""
        obj.who = self.request.user
        return super(BlockEntrySerializer, self).pre_save(obj)

    @list_route(methods=['get'])
    def current(self, request):
        current_blocks = BlockEntry.objects.filter(Q(unblock_at__gt=timezone.now())| Q(unblock_at__isnull=True))
        ser = BlockEntrySerializer(current_blocks, many=True)
        return Response(ser.data)

from rest_framework.views import APIView
class BlockHistory(generics.ListAPIView):
    serializer_class = BlockEntrySerializer

    def get_queryset(self):
        cidr = self.kwargs['cidr']
        return BlockEntry.objects.filter(cidr=cidr)

from rest_framework.response import Response

@api_view(["POST"])
def block(request):
    print 'request is', repr(request.DATA)
    serializer = BlockRequestSerializer(data=request.DATA)
    if serializer.is_valid():
        b = BlockManager().add_block(who=request.user, **serializer.data)
        return Response(BlockEntrySerializer(b).data)
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
