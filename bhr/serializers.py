from foo.models import WhitelistEntry, BlockEntry
from rest_framework import serializers

class WhitelistEntrySerializer(serializers.ModelSerializer):
    who = serializers.SlugField(read_only=True)
    added = serializers.SlugField(read_only=True)
    class Meta:
        model = WhitelistEntry
        fields = ('cidr', 'who', 'why', 'added')


class BlockEntrySerializer(serializers.ModelSerializer):
    who = serializers.SlugField(read_only=True)
    added = serializers.SlugField(read_only=True)
    class Meta:
        model = BlockEntry
        fields = fields = ('cidr', 'who', 'why', 'added', 'unblock_at', 'skip_whitelist')

class BlockRequestSerializer(serializers.Serializer):
    cidr = serializers.CharField(max_length=20)
    source = serializers.CharField(max_length=30)
    why = serializers.CharField()
    duration = serializers.IntegerField(required=False)
    unblock_at = serializers.DateTimeField(required=False)

    def validate(self, attrs):
        if attrs.get('duration') and attrs.get('unblock_at'):
            raise serializers.ValidationError("Specify only one of duration and unblock_at")
        return attrs
