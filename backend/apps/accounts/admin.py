from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Workspace

admin.site.register(Workspace)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ["username", "email", "workspace", "role", "is_online"]
    list_filter = ["role", "workspace", "is_active"]
    fieldsets = UserAdmin.fieldsets + (
        ("Wow Chat", {"fields": ("workspace", "role", "avatar", "is_online")}),
    )
