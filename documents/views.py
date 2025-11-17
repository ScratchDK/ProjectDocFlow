from rest_framework import viewsets, permissions, status
from rest_framework.response import Response

from django.db import models
from .models import Document
from .serializers import DocumentSerializer
from documents.paginators import MyPagination


class DocumentViewSet(viewsets.ModelViewSet):
    queryset = Document.objects.all()
    pagination_class = MyPagination
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Возвращает только документы, к которым у пользователя есть доступ.
        """
        user = self.request.user
        queryset = super().get_queryset()

        # Админы видят всё
        if user.is_staff:
            return queryset

        # Фильтруем документы по правам доступа
        return queryset.filter(
            models.Q(author=user)  # Документы пользователя
            | models.Q(
                allowed_users=user
            )  # Документы, где пользователь в allowed_users
            | models.Q(document_type__in=["general", "review"])  # Общие документы
            | models.Q(
                document_type="private", allowed_users=user
            )  # Приватные, где есть доступ
        ).distinct()

    def create(self, request, *args, **kwargs):
        # Проверяем наличие файла в запросе
        if "file" not in request.FILES:
            return Response(
                {"file": ["Файл не был загружен."]}, status=status.HTTP_400_BAD_REQUEST
            )

        # Добавляем автора перед валидацией
        data = request.data.copy()
        data["author"] = request.user.id

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)

        # Сохраняем документ с файлом
        self.perform_create(serializer)

        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    def perform_create(self, serializer):
        # Сохраняем файл в модель
        serializer.save(author=self.request.user)
