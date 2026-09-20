from django.urls import path
from apps.accounts.views import (
    RegisterView,
    CustomTokenObtainPairView,
    CustomTokenRefreshView,
    CurrentUserView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", CustomTokenObtainPairView.as_view(), name="auth-login"),
    path("refresh/", CustomTokenRefreshView.as_view(), name="auth-refresh"),
    path("me/", CurrentUserView.as_view(), name="auth-me"),
]