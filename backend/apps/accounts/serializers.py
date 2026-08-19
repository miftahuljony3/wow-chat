from django.contrib.auth import get_user_model
from rest_framework import serializers
from .models import Workspace

User = get_user_model()


class WorkspaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workspace
        fields = ["id", "name", "slug", "logo", "created_at"]
        read_only_fields = ["id", "created_at"]


class UserSerializer(serializers.ModelSerializer):
    workspace = WorkspaceSerializer(read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "email", "first_name", "last_name",
                  "role", "avatar", "is_online", "workspace"]
        read_only_fields = ["id", "is_online"]


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    workspace_name = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["username", "email", "password", "first_name",
                  "last_name", "workspace_name"]

    def create(self, validated_data):
        workspace_name = validated_data.pop("workspace_name")
        password = validated_data.pop("password")

        slug = workspace_name.lower().replace(" ", "-")
        workspace, _ = Workspace.objects.get_or_create(
            slug=slug, defaults={"name": workspace_name}
        )

        user = User(**validated_data)
        user.set_password(password)
        user.workspace = workspace
        user.role = User.Role.ADMIN
        user.save()
        return user
