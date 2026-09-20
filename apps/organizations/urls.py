from django.urls import path
from apps.organizations.views import (
    OrganizationListCreateView,
    OrganizationDetailView,
    OrganizationMemberListCreateView,
    OrganizationMemberDetailView,
    OrganizationInviteCreateView,
    OrganizationInviteAcceptView,
)

urlpatterns = [
    # Organizations
    path("", OrganizationListCreateView.as_view(), name="organization-list-create"),
    path("<uuid:id>/", OrganizationDetailView.as_view(), name="organization-detail"),

    # Direct Members Management
    path("<uuid:org_id>/members/", OrganizationMemberListCreateView.as_view(), name="organization-members"),
    path("<uuid:org_id>/members/<uuid:id>/", OrganizationMemberDetailView.as_view(), name="organization-member-detail"),

    # Invitations & RBAC Flow
    path("<uuid:org_id>/invites/", OrganizationInviteCreateView.as_view(), name="organization-invite-create"),
    path("invites/accept/", OrganizationInviteAcceptView.as_view(), name="organization-invite-accept"),
]