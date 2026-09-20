from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from drf_spectacular.utils import extend_schema, OpenApiResponse

from apps.accounts.serializers import (
    RegisterSerializer,
    UserSerializer,
    CustomTokenObtainPairSerializer,
)


class RegisterView(generics.CreateAPIView):
    """
    Register a new user account.
    Validates email uniqueness and strong password criteria.
    """
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Register a new user account",
        responses={
            201: UserSerializer,
            400: OpenApiResponse(description="Validation error"),
        },
    )
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        user_data = UserSerializer(user).data
        return Response(user_data, status=status.HTTP_201_CREATED)


class CustomTokenObtainPairView(TokenObtainPairView):
    """
    Authenticate with email and password to receive JWT access and refresh tokens.
    """
    serializer_class = CustomTokenObtainPairSerializer

    @extend_schema(
        summary="JWT Login",
        responses={
            200: OpenApiResponse(description="Returns access token, refresh token, and user info"),
            401: OpenApiResponse(description="Invalid credentials"),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class CustomTokenRefreshView(TokenRefreshView):
    """
    Refresh an expired JWT access token using a valid refresh token.
    """
    @extend_schema(
        summary="Refresh JWT access token",
        responses={
            200: OpenApiResponse(description="Returns new access token"),
            401: OpenApiResponse(description="Invalid or blacklisted refresh token"),
        },
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class CurrentUserView(APIView):
    """
    Retrieve or update the authenticated user's profile.
    """
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        summary="Get current user profile",
        responses={200: UserSerializer},
    )
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)