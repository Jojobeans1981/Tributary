from rest_framework.views import APIView

from apps.districts.models import District
from apps.districts.serializers import DistrictDetailSerializer, DistrictSerializer
from apps.users.utils import err, ok


class DistrictListView(APIView):
    """GET /api/districts/ — search districts by name and/or state."""

    def get(self, request):
        queryset = District.objects.all()

        search = request.query_params.get("search", "").strip()
        state = request.query_params.get("state", "").strip()

        if search:
            queryset = queryset.filter(name__icontains=search)
        if state:
            queryset = queryset.filter(state__iexact=state)

        queryset = queryset.order_by("name")[:10]

        serializer = DistrictSerializer(queryset, many=True)
        return ok(serializer.data)


class DistrictDetailView(APIView):
    """GET /api/districts/{nces_id}/ — district detail + members list."""

    def get(self, request, nces_id):
        try:
            district = District.objects.get(nces_id=nces_id)
        except District.DoesNotExist:
            return err("NOT_FOUND", "District not found.", status=404)

        serializer = DistrictDetailSerializer(district)
        return ok(serializer.data)
