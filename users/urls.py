import users.views as views
from django.urls import path
from users.apps import UsersConfig
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

app_name = UsersConfig.name

urlpatterns = [
    path("login/", TokenObtainPairView.as_view(), name="login"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path(
        "users/<str:email>/",
        views.CustomUserDetailAPIView.as_view(),
        name="users_detail",
    ),
    path("users/", views.CustomUserListAPIView.as_view(), name="users"),
    path("register/", views.CustomUserCreateAPIView.as_view(), name="users_create"),
    path(
        "users/update/<str:email>/",
        views.CustomUserUpdateAPIView.as_view(),
        name="users_update",
    ),
    path(
        "users/delete/<str:email>/",
        views.CustomUserDeleteAPIView.as_view(),
        name="users_delete",
    ),
    path(
        "api/connect-telegram/",
        views.ConnectTelegramView.as_view(),
        name="connect-telegram",
    ),
]
