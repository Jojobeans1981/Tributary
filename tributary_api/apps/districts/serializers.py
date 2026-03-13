from rest_framework import serializers

from apps.districts.models import District


class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = [
            "id",
            "nces_id",
            "name",
            "state",
            "locale_type",
            "enrollment",
            "frl_pct",
            "ell_pct",
            "data_vintage",
        ]


class DistrictMemberSerializer(serializers.Serializer):
    id = serializers.UUIDField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()
    role = serializers.CharField()


class DistrictDetailSerializer(serializers.ModelSerializer):
    members = serializers.SerializerMethodField()

    class Meta:
        model = District
        fields = [
            "id",
            "nces_id",
            "name",
            "state",
            "locale_type",
            "enrollment",
            "frl_pct",
            "ell_pct",
            "data_vintage",
            "members",
        ]

    def get_members(self, obj):
        members = obj.members.filter(is_active=True).order_by("date_joined")[:50]
        return DistrictMemberSerializer(members, many=True).data
