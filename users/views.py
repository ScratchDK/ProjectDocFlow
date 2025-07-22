from rest_framework import generics
from users.models import CustomUser
from documents.paginators import MyPagination
from users.permissions import IsOwnerOrAdmin, IsProfileOwner
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from users.serializers import (
    CustomUserSerializer,
    PublicUserSerializer,
    PrivateUserSerializer,
    TelegramConnectSerializer,
)


# POST
class CustomUserCreateAPIView(generics.CreateAPIView):
    serializer_class = CustomUserSerializer
    queryset = CustomUser.objects.all()
    permission_classes = [AllowAny]

    def perform_create(self, serializer):
        password = serializer.validated_data.get("password")
        user = serializer.save(is_active=True)
        user.set_password(password)
        user.save()


# PATCH
class CustomUserUpdateAPIView(generics.UpdateAPIView):
    serializer_class = CustomUserSerializer
    queryset = CustomUser.objects.all()
    lookup_field = "email"
    permission_classes = [IsAuthenticated, IsOwnerOrAdmin]


# DELETE
class CustomUserDeleteAPIView(generics.DestroyAPIView):
    queryset = CustomUser.objects.all()
    lookup_field = "email"
    permission_classes = [IsAuthenticated, IsAdminUser]


# GET
class CustomUserListAPIView(generics.ListAPIView):
    serializer_class = CustomUserSerializer
    pagination_class = MyPagination
    queryset = CustomUser.objects.all()
    permission_classes = [IsAdminUser]


# GET
class CustomUserDetailAPIView(generics.RetrieveAPIView):
    serializer_class = CustomUserSerializer
    queryset = CustomUser.objects.all()
    lookup_field = "email"
    permission_classes = [IsAuthenticated, IsProfileOwner]

    def get_serializer_class(self):
        if self.request.user == self.get_object():
            return PrivateUserSerializer
        return PublicUserSerializer

    def get_permissions(self):
        if self.request.method == "GET":
            return [IsAuthenticated()]
        return [IsAuthenticated(), IsProfileOwner()]


class ConnectTelegramView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        serializer = TelegramConnectSerializer(
            instance=request.user, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"status": "Telegram chat ID успешно сохранен"},
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
