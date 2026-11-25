from rest_framework.permissions import SAFE_METHODS, BasePermission

from login.permissions import is_administrator


class AdminOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or is_administrator(request.user)
