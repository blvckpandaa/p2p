from rest_framework import permissions
from django.db.models import Q

class HasP2PAccess(permissions.BasePermission):
    """
    Проверяет, имеет ли пользователь доступ к P2P-бирже.
    Доступ имеют только пользователи, которые участвуют в стейкинге.
    """
    
    def has_permission(self, request, view):
        """Проверка доступа"""
        return request.user.has_p2p_access


class IsOrderOwner(permissions.BasePermission):
    """
    Проверяет, является ли пользователь владельцем ордера.
    """
    
    def has_object_permission(self, request, view, obj):
        """Проверка на уровне объекта"""
        return obj.user == request.user


class IsTransactionParticipant(permissions.BasePermission):
    """
    Проверяет, является ли пользователь участником транзакции (покупателем или продавцом).
    """
    
    def has_object_permission(self, request, view, obj):
        """Проверка на уровне объекта"""
        return obj.buyer == request.user or obj.seller == request.user 