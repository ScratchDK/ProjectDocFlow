import os
from django.db import models
from django.utils import timezone


class Document(models.Model):
    DOCUMENT_TYPES = (
        ("signature", "На подпись"),
        ("general", "Общий"),
        ("review", "Для ознакомления"),
        ("private", "Приватный"),
    )

    DOCUMENT_STATUS = (
        ("pending", "На рассмотрении"),
        ("approved", "Подтвержден"),
        ("rejected", "Отклонен"),
    )

    def get_upload_path(self, filename):
        """Генерирует путь для сохранения файла на основе типа документа"""
        # Получаем текстовое представление типа документа
        type_folder = self.get_document_type_display().lower()

        # Формируем путь: documents/Документы/{тип}/{год}/{месяц}/{день}/{filename}
        return os.path.join(
            "documents",
            "Документы",
            type_folder,
            timezone.now().strftime("%Y"),
            timezone.now().strftime("%m"),
            timezone.now().strftime("%d"),
            filename,
        )

    author = models.ForeignKey(
        "users.CustomUser",
        on_delete=models.CASCADE,
        related_name="uploaded_documents",
        verbose_name="Автор",
    )
    title = models.CharField(max_length=255, verbose_name="Название документа")
    description = models.TextField(blank=True, null=True, verbose_name="Описание")
    file = models.FileField(upload_to=get_upload_path, verbose_name="Файл")
    uploaded_at = models.DateTimeField(
        default=timezone.now, verbose_name="Дата загрузки"
    )
    allowed_users = models.ManyToManyField(
        "users.CustomUser",
        related_name="accessible_documents",
        blank=True,
        verbose_name="Пользователи с доступом",
    )
    document_type = models.CharField(
        max_length=20,
        choices=DOCUMENT_TYPES,
        default="general",
        verbose_name="Тип документа",
    )
    status = models.CharField(
        max_length=20, choices=DOCUMENT_STATUS, default="pending", verbose_name="Статус"
    )

    def __str__(self):
        return f"{self.title}"

    def get_users_with_access(self):
        """
        Возвращает queryset пользователей с доступом к документу.
        """
        if self.allowed_users.exists():
            return self.allowed_users.all() | self.author.__class__.objects.filter(
                pk=self.author.pk
            )
        return self.author.__class__.objects.all()

    def has_access(self, user):
        """
        Проверяет доступ конкретного пользователя с учётом типа документа.
        """
        if not user.is_authenticated:
            return False

        # Админ всегда имеет доступ
        if user.is_staff:
            return True

        # Автор всегда имеет доступ
        if user == self.author:
            return True

        # Для приватных документов и документов на подпись - только allowed_users
        if self.document_type in ["private", "signature"]:
            return self.allowed_users.filter(pk=user.pk).exists()

        # Для общих документов и документов для ознакомления - доступ у всех
        return True

    class Meta:
        verbose_name = "Документ"
        verbose_name_plural = "Документы"
        ordering = ["-uploaded_at"]
