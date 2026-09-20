import secrets
from datetime import timedelta
from django.conf import settings
from django.db import models
from django.utils import timezone
from apps.common.models import TimeStampedUUIDModel


class Organization(TimeStampedUUIDModel):
    """
    Tenant entity representing an isolated workspace or company account.
    """
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "organizations"
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name


class MembershipRole(models.TextChoices):
    OWNER = "OWNER", "Owner"
    ADMIN = "ADMIN", "Admin"
    MEMBER = "MEMBER", "Member"


class Membership(TimeStampedUUIDModel):
    """
    Links a User to an Organization with a defined RBAC role.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
        db_index=True,
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="memberships",
        db_index=True,
    )
    role = models.CharField(
        max_length=20,
        choices=MembershipRole.choices,
        default=MembershipRole.MEMBER,
        db_index=True,
    )

    class Meta:
        db_table = "organization_memberships"
        verbose_name = "Organization Membership"
        verbose_name_plural = "Organization Memberships"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "organization"],
                name="unique_user_organization_membership",
            )
        ]
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} -> {self.organization.name} ({self.role})"


class InvitationStatus(models.TextChoices):
    PENDING = "PENDING", "Pending"
    ACCEPTED = "ACCEPTED", "Accepted"
    REVOKED = "REVOKED", "Revoked"


class Invitation(TimeStampedUUIDModel):
    """
    Pending invitations sent to prospective or existing users to join an organization.
    """
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="invitations",
        db_index=True,
    )
    email = models.EmailField(db_index=True)
    role = models.CharField(
        max_length=20,
        choices=MembershipRole.choices,
        default=MembershipRole.MEMBER,
    )
    token = models.CharField(max_length=64, unique=True, db_index=True)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="sent_invitations",
    )
    status = models.CharField(
        max_length=20,
        choices=InvitationStatus.choices,
        default=InvitationStatus.PENDING,
        db_index=True,
    )
    expires_at = models.DateTimeField()

    class Meta:
        db_table = "organization_invitations"
        verbose_name = "Organization Invitation"
        verbose_name_plural = "Organization Invitations"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "email", "status"],
                name="unique_active_invitation_per_org_email",
            )
        ]

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = secrets.token_urlsafe(32)
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(days=7)
        super().save(*args, **kwargs)

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Invite for {self.email} to {self.organization.name} [{self.status}]"