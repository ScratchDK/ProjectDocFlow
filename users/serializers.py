from rest_framework import serializers
from .models import CustomUser


class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "email",
            "password",
            "groups",
            "first_name",
            "last_name",
            "phone_number",
            "avatar",
            "city",
            "confirmation_token",
            "is_active",
            "is_staff",
            "date_joined",
        ]
        extra_kwargs = {
            "password": {
                "write_only": True,
                "required": True,
            },  # Пароль не будет отображаться в API
            "confirmation_token": {"read_only": True},  # Токен только для чтения
        }


class PublicUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "first_name",
            "phone_number",
            "city",
            "email",
            "avatar",
            "date_joined",
        ]
        read_only_fields = fields


class PrivateUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "phone_number",
            "city",
            "email",
            "avatar",
            "date_joined",
            "payments",
        ]


class TelegramConnectSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ["telegram_chat_id"]
        extra_kwargs = {"telegram_chat_id": {"required": True}}
