import documents.views as views
from rest_framework.routers import DefaultRouter

app_name = "document"

router = DefaultRouter()

router.register("document", views.DocumentViewSet, basename="document")

urlpatterns = [] + router.urls
