from rest_framework import serializers
from .models import Document
from users.models import CustomUser


class DocumentSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField(read_only=True)  # Только для чтения
    allowed_users = serializers.ListField(  # Для приёма списка email
        child=serializers.EmailField(),
        write_only=True,
        required=False,
        help_text="Список email через запятую: user1@example.com,user2@example.com",
    )

    class Meta:
        model = Document
        fields = [
            "id",
            "author",
            "title",
            "description",
            "file",
            "uploaded_at",
            "allowed_users",
            "document_type",
            "status",
        ]
        read_only_fields = [
            "author",
            "uploaded_at",
            "status",
        ]

    def create(self, validated_data):
        emails = validated_data.pop("allowed_users", [])
        document = Document.objects.create(**validated_data)

        if emails:
            users = CustomUser.objects.filter(email__in=emails)
            document.allowed_users.set(users)

        return document
