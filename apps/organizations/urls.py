from django.urls import path
from apps.organizations.views import (
    OrganizationListCreateView,
    OrganizationDetailView,
    OrganizationMemberListCreateView,
    OrganizationMemberDetailView,
)

urlpatterns = [
    path("", OrganizationListCreateView.as_view(), name="organization-list-create"),
    path("<uuid:id>/", OrganizationDetailView.as_view(), name="organization-detail"),
    path("<uuid:org_id>/members/", OrganizationMemberListCreateView.as_view(), name="organization-members"),
    path("<uuid:org_id>/members/<uuid:id>/", OrganizationMemberDetailView.as_view(), name="organization-member-detail"),
]