import os
from unittest.mock import MagicMock, patch

from django.conf import settings
from django.contrib.messages.storage.fallback import FallbackStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import RequestFactory, TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient, APITestCase

from documents.admin import DocumentAdmin, approve_documents, reject_documents
from documents.models import Document
from documents.serializers import DocumentSerializer
from documents.views import DocumentViewSet
from users.models import CustomUser


class DocumentModelTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="user@example.com",
            password="testpass123",
            telegram_chat_id="12345",
            username="user1",
        )
        self.admin = CustomUser.objects.create_user(
            email="admin@example.com",
            password="adminpass123",
            is_staff=True,
            telegram_chat_id="67890",
            username="admin1",
        )
        self.other_user = CustomUser.objects.create_user(
            email="other@example.com", password="otherpass123", username="other_user"
        )

        self.document_data = {
            "title": "Test Document",
            "description": "Test Description",
            "file": SimpleUploadedFile("test.txt", b"file_content"),
            "document_type": "general",
        }

    def test_document_creation(self):
        """Тест создания документа"""
        document = Document.objects.create(author=self.user, **self.document_data)
        self.assertEqual(document.title, "Test Document")
        self.assertEqual(document.status, "pending")
        self.assertEqual(document.author, self.user)

    def test_get_upload_path(self):
        """Тест генерации пути для загрузки файла"""
        document = Document.objects.create(author=self.user, **self.document_data)

        now = timezone.now()
        year = now.strftime("%Y")
        month = now.strftime("%m")
        day = now.strftime("%d")

        path = document.get_upload_path("test.txt")
        expected_path = os.path.join(
            "documents", "Документы", "общий", year, month, day, "test.txt"
        )
        self.assertEqual(path, expected_path)

    def test_has_access_method(self):
        """Тест метода проверки доступа к документу"""
        # Создаем документы разных типов
        general_doc = Document.objects.create(author=self.user, **self.document_data)
        private_doc = Document.objects.create(
            author=self.user, **{**self.document_data, "document_type": "private"}
        )
        signature_doc = Document.objects.create(
            author=self.user, **{**self.document_data, "document_type": "signature"}
        )

        # Проверяем доступ для разных пользователей
        # Админ имеет доступ ко всем документам
        self.assertTrue(general_doc.has_access(self.admin))
        self.assertTrue(private_doc.has_access(self.admin))
        self.assertTrue(signature_doc.has_access(self.admin))

        # Автор имеет доступ ко всем своим документам
        self.assertTrue(general_doc.has_access(self.user))
        self.assertTrue(private_doc.has_access(self.user))
        self.assertTrue(signature_doc.has_access(self.user))

        # Другие пользователи
        # Общий документ - доступ у всех
        self.assertTrue(general_doc.has_access(self.other_user))
        # Приватный документ - только у автора и allowed_users
        self.assertFalse(private_doc.has_access(self.other_user))
        # Документ на подпись - только у автора и allowed_users
        self.assertFalse(signature_doc.has_access(self.other_user))

        # Добавляем пользователя в allowed_users
        private_doc.allowed_users.add(self.other_user)
        signature_doc.allowed_users.add(self.other_user)
        self.assertTrue(private_doc.has_access(self.other_user))
        self.assertTrue(signature_doc.has_access(self.other_user))

    def test_get_users_with_access(self):
        """Тест метода получения пользователей с доступом"""
        doc = Document.objects.create(author=self.user, **self.document_data)

        # Без allowed_users возвращает всех пользователей
        self.assertEqual(
            doc.get_users_with_access().count(), CustomUser.objects.all().count()
        )

        # С allowed_users возвращает только их + автора
        doc.allowed_users.add(self.other_user)
        self.assertEqual(doc.get_users_with_access().count(), 2)  # author + other_user


class DocumentViewSetTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="user@example.com", password="testpass123", username="user1"
        )
        self.admin = CustomUser.objects.create_user(
            email="admin@example.com",
            password="adminpass123",
            is_staff=True,
            username="admin1",
        )
        self.other_user = CustomUser.objects.create_user(
            email="other@example.com", password="otherpass123", username="other_user"
        )

        self.client = APIClient()
        self.factory = RequestFactory()

        self.document_data = {
            "title": "Test Document",
            "description": "Test Description",
            "file": SimpleUploadedFile("test.txt", b"file_content"),
            "document_type": "general",
        }

        # Создаем документы разных типов
        self.general_doc = Document.objects.create(
            author=self.user, **self.document_data
        )
        self.private_doc = Document.objects.create(
            author=self.user, **{**self.document_data, "document_type": "private"}
        )
        self.signature_doc = Document.objects.create(
            author=self.user, **{**self.document_data, "document_type": "signature"}
        )
        self.review_doc = Document.objects.create(
            author=self.user, **{**self.document_data, "document_type": "review"}
        )

    def test_get_queryset_for_admin(self):
        """Админ видит все документы"""
        request = self.factory.get("/documents/")
        request.user = self.admin
        view = DocumentViewSet()
        view.request = request

        queryset = view.get_queryset()
        self.assertEqual(queryset.count(), Document.objects.count())

    def test_get_queryset_for_regular_user(self):
        """Обычный пользователь видит только доступные документы"""
        request = self.factory.get("/documents/")
        request.user = self.other_user
        view = DocumentViewSet()
        view.request = request

        queryset = view.get_queryset()
        # Должен видеть только общие документы и для ознакомления
        self.assertEqual(queryset.count(), 2)  # general_doc и review_doc

        # Добавляем доступ к приватному документу
        self.private_doc.allowed_users.add(self.other_user)
        queryset = view.get_queryset()
        self.assertEqual(queryset.count(), 3)  # + private_doc

    def test_create_document(self):
        """Тест создания документа через API"""
        initial_count = (
            Document.objects.count()
        )  # Получаем текущее количество документов

        self.client.force_authenticate(user=self.user)
        url = reverse("documents:document-list")

        # Создаем временный файл для теста
        with open("test_file.txt", "w") as f:
            f.write("Test file content")

        with open("test_file.txt", "rb") as f:
            response = self.client.post(
                url,
                {
                    "title": "New Document",
                    "description": "New Description",
                    "file": f,
                    "document_type": "general",
                    "allowed_users": ["other@example.com"],
                },
                format="multipart",
            )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Document.objects.count(), initial_count + 1)

        new_document = Document.objects.get(title="New Document")
        self.assertEqual(new_document.title, "New Document")
        self.assertEqual(new_document.description, "New Description")
        self.assertTrue(
            new_document.allowed_users.filter(email="other@example.com").exists()
        )

        # Удаляем временный файл
        if os.path.exists("test_file.txt"):
            os.remove("test_file.txt")

    def test_create_document_without_file(self):
        """Попытка создать документ без файла"""
        self.client.force_authenticate(user=self.user)
        url = reverse("documents:document-list")

        response = self.client.post(
            url,
            {
                "title": "New Document",
                "description": "New Description",
                "document_type": "general",
            },
            format="multipart",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("file", response.data)

    def test_document_detail_access(self):
        """Тест доступа к деталям документа"""
        # Добавляем other_user в allowed_users приватного документа
        self.private_doc.allowed_users.add(self.other_user)

        # Анонимный пользователь не имеет доступа
        url = reverse("documents:document-detail", args=[self.general_doc.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Автор имеет доступ ко всем своим документам
        self.client.force_authenticate(user=self.user)
        for doc in [
            self.general_doc,
            self.private_doc,
            self.signature_doc,
            self.review_doc,
        ]:
            url = reverse("documents:document-detail", args=[doc.id])
            response = self.client.get(url)
            self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Другой пользователь имеет доступ только к общим документам и документам для ознакомления
        self.client.force_authenticate(user=self.other_user)

        # Общий документ - доступ есть
        url = reverse("documents:document-detail", args=[self.general_doc.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Документ для ознакомления - доступ есть
        url = reverse("documents:document-detail", args=[self.review_doc.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Приватный документ - доступ есть (т.к. мы добавили в allowed_users)
        url = reverse("documents:document-detail", args=[self.private_doc.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Документ на подпись - доступа нет (не в allowed_users)
        url = reverse("documents:document-detail", args=[self.signature_doc.id])
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)


class DocumentSerializerTests(TestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="user@example.com", password="testpass123", username="user1"
        )
        self.other_user = CustomUser.objects.create_user(
            email="other@example.com", password="otherpass123", username="other_user"
        )

        self.document_data = {
            "title": "Test Document",
            "description": "Test Description",
            "file": SimpleUploadedFile("test.txt", b"file_content"),
            "document_type": "general",
            "author": self.user,
        }

    def test_serializer_with_allowed_users(self):
        """Тест сериализатора с allowed_users"""
        data = {
            "title": "New Document",
            "description": "New Description",
            "file": SimpleUploadedFile("test.txt", b"file_content"),
            "document_type": "general",
            "allowed_users": ["other@example.com"],
        }

        serializer = DocumentSerializer(data=data)
        self.assertTrue(serializer.is_valid())

        document = serializer.save(author=self.user)
        self.assertEqual(document.title, "New Document")
        self.assertTrue(
            document.allowed_users.filter(email="other@example.com").exists()
        )

    def test_serializer_with_invalid_email(self):
        """Тест сериализатора с невалидным email в allowed_users"""
        data = {
            "title": "New Document",
            "description": "New Description",
            "file": SimpleUploadedFile("test.txt", b"file_content"),
            "document_type": "general",
            "allowed_users": ["invalid-email"],
        }

        serializer = DocumentSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn("allowed_users", serializer.errors)


class DocumentAdminTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

        self.admin = CustomUser.objects.create_superuser(
            email="admin@example.com", password="adminpass123", username="admin1"
        )
        self.user = CustomUser.objects.create_user(
            email="user@example.com",
            password="testpass123",
            telegram_chat_id="12345",
            telegram_notifications=True,
            username="user1",
        )

        self.document = Document.objects.create(
            author=self.user,
            title="Test Document",
            description="Test Description",
            file=SimpleUploadedFile("test.txt", b"file_content"),
            document_type="general",
            status="pending",
        )

    def _get_request(self, user):
        """Создает запрос с поддержкой messages"""
        request = self.factory.get("/")
        request.user = user
        setattr(request, "session", "session")
        setattr(request, "_messages", FallbackStorage(request))
        return request

    @patch("documents.admin.send_status_notification.delay")
    @patch("documents.admin.send_telegram_notification.delay")
    def test_approve_documents_action(self, mock_telegram, mock_email):
        """Тест действия approve_documents в админке"""

        request = self._get_request(self.admin)
        modeladmin = DocumentAdmin(Document, None)
        queryset = Document.objects.filter(pk=self.document.pk)

        # Действие
        approve_documents(modeladmin, request, queryset)

        self.document.refresh_from_db()
        self.assertEqual(self.document.status, "approved")

        # Проверяем, что задачи на отправку уведомлений были вызваны
        # Проверяем параметры вызовов уведомлений
        mock_email.assert_called_once_with(
            user_email=self.user.email,
            doc_title="Test Document",
            status="подтверждён",
            doc_url="http://testserver/document/1/",
        )
        mock_telegram.assert_called_once()

    @patch("documents.admin.send_telegram_notification.delay")
    @patch("documents.admin.send_status_notification.delay")
    def test_reject_documents_action(self, mock_email, mock_telegram):
        """Тест отклонения документов"""

        # Подготовка
        request = self._get_request(self.admin)
        modeladmin = DocumentAdmin(Document, None)
        queryset = Document.objects.filter(pk=self.document.pk)

        # Действие
        reject_documents(modeladmin, request, queryset)

        # Проверки
        self.document.refresh_from_db()
        self.assertEqual(self.document.status, "rejected")

        # Проверяем параметры вызовов уведомлений
        mock_email.assert_called_once_with(
            user_email=self.user.email,
            doc_title="Test Document",
            status="отклонён",
            doc_url="http://testserver/document/2/",
        )
        mock_telegram.assert_called_once()


class DocumentSignalsTests(TestCase):
    @patch("documents.signals.send_mail")
    @patch("documents.signals.send_telegram_notification.delay")
    def test_notify_admin_on_upload(self, mock_telegram, mock_email):
        """Тест сигнала уведомления админа о загрузке документа"""
        admin = CustomUser.objects.create_superuser(
            email="admin@example.com",
            password="adminpass123",
            telegram_chat_id="12345",
            telegram_notifications=True,
            username="admin1",
        )
        user = CustomUser.objects.create_user(
            email="user@example.com", password="testpass123", username="user1"
        )

        doc = Document.objects.create(
            author=user,
            title="Test Document",
            description="Test Description",
            file=SimpleUploadedFile("test.txt", b"file_content"),
            document_type="general",
        )

        # Проверяем, что отправка email была вызвана
        mock_email.assert_called_once()

        # Проверяем, что отправка telegram была вызвана
        mock_telegram.assert_called_once()


class DocumentTasksTests(TestCase):
    @patch("documents.tasks.Bot")
    def test_send_telegram_notification(self, mock_bot):
        """Тест задачи отправки telegram-уведомления"""
        from documents.tasks import send_telegram_notification

        # Настраиваем mock для Bot
        mock_bot_instance = MagicMock()
        mock_bot.return_value = mock_bot_instance

        chat_id = "12345"
        message_lines = ["Line 1", "Line 2"]

        # Вызываем задачу
        send_telegram_notification(chat_id, message_lines)

        # Проверяем, что Bot был создан с правильным токеном
        mock_bot.assert_called_once_with(token=settings.TELEGRAM_BOT_TOKEN)

        # Проверяем, что сообщение было отправлено
        mock_bot_instance.send_message.assert_called_once_with(
            chat_id=chat_id,
            text="Line 1\nLine 2",
            parse_mode="Markdown",
        )

    @patch("documents.tasks.send_mail")
    def test_send_status_notification(self, mock_send_mail):
        """Тест задачи отправки email-уведомления"""
        from documents.tasks import send_status_notification

        user_email = "user@example.com"
        doc_title = "Test Document"
        status = "approved"
        doc_url = "http://example.com/doc/1"

        # Вызываем задачу
        send_status_notification(user_email, doc_title, status, doc_url)

        # Проверяем позиционные аргументы
        args, kwargs = mock_send_mail.call_args
        self.assertEqual(args[0], f"Статус документа: {doc_title}")
        self.assertEqual(
            args[1],
            f'Ваш документ "{doc_title}" был {status}.\nПроверьте в системе: {doc_url}',
        )
        self.assertEqual(kwargs["from_email"], None)
        self.assertEqual(kwargs["recipient_list"], [user_email])
        self.assertEqual(kwargs["fail_silently"], False)


class PaginationTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            email="user@example.com", password="testpass123", username="user1"
        )
        self.client.force_authenticate(user=self.user)

        # Создаем несколько документов для тестирования пагинации
        for i in range(10):
            Document.objects.create(
                author=self.user,
                title=f"Document {i}",
                file=SimpleUploadedFile(f"test_{i}.txt", b"file_content"),
                document_type="general",
            )

    def test_pagination(self):
        """Тест пагинации документов"""
        url = reverse("documents:document-list")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 5)  # page_size по умолчанию

        # Проверяем наличие ключей пагинации
        self.assertIn("count", response.data)
        self.assertIn("next", response.data)
        self.assertIn("previous", response.data)
        self.assertIn("results", response.data)

    def test_custom_page_size(self):
        """Тест изменения размера страницы"""
        url = reverse("documents:document-list") + "?page_size=2"
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["results"]), 2)
