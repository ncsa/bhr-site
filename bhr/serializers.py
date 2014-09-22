from bhr.models import WhitelistEntry, Block, BlockEntry
from rest_framework import serializers
from bhr.models import is_whitelisted

class WhitelistEntrySerializer(serializers.ModelSerializer):
    who = serializers.SlugField(read_only=True)
    added = serializers.SlugField(read_only=True)
    class Meta:
        model = WhitelistEntry
        fields = ('cidr', 'who', 'why', 'added')

class BlockSerializer(serializers.HyperlinkedModelSerializer):
    who = serializers.SlugField(read_only=True)
    set_blocked = serializers.HyperlinkedIdentityField(view_name='block-set-blocked', lookup_field='pk')
    class Meta:
        model = Block
        fields = ('who', 'url', 'cidr', 'source', 'why', 'added', 'unblock_at', 'skip_whitelist', 'set_blocked')

class BlockBriefSerializer(serializers.ModelSerializer):
    who = serializers.SlugField(read_only=True)
    class Meta:
        model = Block
        fields = ('cidr', )

class BlockQueueSerializer(serializers.ModelSerializer):
    set_blocked = serializers.HyperlinkedIdentityField(view_name='block-set-blocked', lookup_field='pk')
    class Meta:
        model = Block
        fields = ('id', 'cidr', 'set_blocked')

class BlockEntrySerializer(serializers.HyperlinkedModelSerializer):
    block = BlockBriefSerializer()
    set_unblocked = serializers.HyperlinkedIdentityField(view_name='blockentry-set-unblocked', lookup_field='pk')
    class Meta:
        model = BlockEntry
        fields = ('block', 'ident', 'added', 'removed', 'set_unblocked')

class UnBlockEntrySerializer(serializers.HyperlinkedModelSerializer):
    block = BlockBriefSerializer()
    set_unblocked = serializers.HyperlinkedIdentityField(view_name='blockentry-set-unblocked', lookup_field='pk')
    class Meta:
        model = BlockEntry
        fields = ('id', 'block', 'ident', 'added', 'set_unblocked')

class BlockRequestSerializer(serializers.Serializer):
    cidr = serializers.CharField(max_length=20)
    source = serializers.CharField(max_length=30)
    why = serializers.CharField()
    duration = serializers.IntegerField(required=False)
    unblock_at = serializers.DateTimeField(required=False)
    skip_whitelist = serializers.BooleanField(default=False)

    def validate(self, attrs):
        if attrs.get('duration') and attrs.get('unblock_at'):
            raise serializers.ValidationError("Specify only one of duration and unblock_at")

        cidr = attrs.get('cidr')
        skip_whitelist = attrs.get('skip_whitelist')
        if cidr and not skip_whitelist:
            item = is_whitelisted(cidr)
            if item:
                raise serializers.ValidationError("whitelisted: %s: %s" % (item.who, item.why))

        return attrs

class SetBlockedSerializer(serializers.Serializer):
    ident = serializers.CharField()

class UnblockNowSerializer(serializers.Serializer):
    cidr = serializers.CharField(max_length=20)
    why = serializers.CharField()
