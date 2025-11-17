from django.contrib import admin
from .models import CustomUser


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = (
        "email",
        "username",
        "phone_number",
        "city",
        "is_staff",
        "last_login",
        "telegram_notifications",
        "telegram_chat_id",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "city")
    search_fields = ("email", "username", "phone_number")
    ordering = ("email",)
