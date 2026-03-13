from django.urls import path

from apps.districts.views import DistrictDetailView, DistrictListView

urlpatterns = [
    path("districts/", DistrictListView.as_view(), name="district-list"),
    path("districts/<str:nces_id>/", DistrictDetailView.as_view(), name="district-detail"),
]
