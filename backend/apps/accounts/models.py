import uuid
from django.contrib.auth.models import AbstractUser
from django.db import models


class Workspace(models.Model):
    """
    Multi-tenant root. Every channel integration and conversation belongs
    to exactly one Workspace.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    logo = models.ImageField(upload_to="workspaces/logos/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class User(AbstractUser):
    """Custom user — can belong to one Workspace with a role."""

    class Role(models.TextChoices):
        SUPER_ADMIN = "super_admin", "Super Admin"
        ADMIN = "admin", "Admin"
        AGENT = "agent", "Agent"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="users",
        null=True,
        blank=True,
    )
    role = models.CharField(
        max_length=20, choices=Role.choices, default=Role.AGENT
    )
    avatar = models.ImageField(upload_to="users/avatars/", blank=True, null=True)
    is_online = models.BooleanField(default=False)

    class Meta:
        ordering = ["username"]

    def __str__(self):
        return f"{self.username} ({self.workspace})"
