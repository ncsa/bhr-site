from bhr.models import WhitelistEntry, Block, BlockEntry
from rest_framework import serializers
from bhr.models import BHRDB, is_whitelisted, is_prefixlen_too_small, is_source_blacklisted

from bhr.util import expand_time


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


class BlockLimitedSerializer(serializers.ModelSerializer):
    class Meta:
        model = Block
        fields = ('cidr', 'source', 'added', 'unblock_at')


class BlockBriefSerializer(serializers.ModelSerializer):
    class Meta:
        model = Block
        fields = ('cidr', )


class BlockQueueSerializer(serializers.ModelSerializer):
    set_blocked = serializers.HyperlinkedIdentityField(view_name='block-set-blocked', lookup_field='pk')

    class Meta:
        model = Block
        fields = ('id', 'cidr', 'set_blocked', 'added')


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
    cidr = serializers.CharField(max_length=50)
    source = serializers.CharField(max_length=30)
    why = serializers.CharField()
    duration = serializers.CharField(required=True)
    unblock_at = serializers.DateTimeField(required=False)
    skip_whitelist = serializers.BooleanField(default=False)
    autoscale = serializers.BooleanField(default=False)
    extend = serializers.BooleanField(default=True)

    def validate_duration(self, value):
        try:
            expand_time(value)
        except ValueError:
            raise serializers.ValidationError("Invalid duration")
        return value

    def validate(self, attrs):
        if attrs.get('duration') and attrs.get('unblock_at'):
            raise serializers.ValidationError("Specify only one of duration and unblock_at")

        cidr = attrs.get('cidr')
        source = attrs.get('source')
        skip_whitelist = attrs.get('skip_whitelist')
        if cidr and not skip_whitelist:
            item = is_whitelisted(cidr)
            if item:
                raise serializers.ValidationError("whitelisted: %s: %s" % (item.who, item.why))
            if is_prefixlen_too_small(cidr):
                raise serializers.ValidationError("Prefix length in %s is too small" % cidr)
            item = is_source_blacklisted(source)
            if item:
                raise serializers.ValidationError("Source %s is blacklisted: %s: %s" % (source, item.who, item.why))

        return attrs


class SetBlockedSerializer(serializers.Serializer):
    ident = serializers.CharField()


class UnblockNowSerializer(serializers.Serializer):
    cidr = serializers.CharField(max_length=50)
    why = serializers.CharField()

    def validate_cidr(self, value):
        cidr = value
        b = BHRDB().get_block(cidr)
        if not b:
            raise serializers.ValidationError("%s is not currently blocked" % cidr)
        return cidr
