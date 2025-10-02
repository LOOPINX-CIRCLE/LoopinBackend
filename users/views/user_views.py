"""
User-related views for Django REST Framework.
"""

from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404

from users.models import UserProfile
from users.serializers.user_serializers import (
    UserSerializer,
    UserCreateSerializer,
    UserUpdateSerializer,
    UserProfileSerializer,
    UserProfileUpdateSerializer,
    UserWithProfileSerializer,
)


class UserListCreateView(generics.ListCreateAPIView):
    """List all users or create a new user."""
    
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return UserCreateSerializer
        return UserSerializer
    
    def get_permissions(self):
        """Only staff can list users, anyone can create."""
        if self.request.method == 'GET':
            return [permissions.IsAdminUser()]
        return [permissions.AllowAny()]


class UserRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a user."""
    
    queryset = User.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return UserUpdateSerializer
        return UserWithProfileSerializer
    
    def get_permissions(self):
        """Users can only access their own profile unless they're staff."""
        if self.request.method == 'GET':
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]
    
    def get_object(self):
        """Ensure users can only access their own profile unless they're staff."""
        obj = super().get_object()
        user = self.request.user
        
        if not user.is_staff and obj != user:
            self.permission_denied(self.request, message="You can only access your own profile.")
        
        return obj
    
    def perform_destroy(self, instance):
        """Soft delete by deactivating user."""
        instance.is_active = False
        instance.save()


class UserProfileView(generics.RetrieveUpdateAPIView):
    """Retrieve or update user profile."""
    
    serializer_class = UserProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_object(self):
        """Get or create profile for the current user."""
        profile, created = UserProfile.objects.get_or_create(
            user=self.request.user,
            defaults={}
        )
        return profile
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return UserProfileUpdateSerializer
        return UserProfileSerializer


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def current_user_view(request):
    """Get current authenticated user information."""
    serializer = UserWithProfileSerializer(request.user)
    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def change_password_view(request):
    """Change user password."""
    user = request.user
    old_password = request.data.get('old_password')
    new_password = request.data.get('new_password')
    
    if not old_password or not new_password:
        return Response(
            {'error': 'Both old_password and new_password are required.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not user.check_password(old_password):
        return Response(
            {'error': 'Old password is incorrect.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if len(new_password) < 8:
        return Response(
            {'error': 'New password must be at least 8 characters long.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user.set_password(new_password)
    user.save()
    
    return Response({'message': 'Password changed successfully.'})


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def activate_user_view(request, user_id):
    """Activate a deactivated user (admin only)."""
    user = get_object_or_404(User, id=user_id)
    user.is_active = True
    user.save()
    
    return Response({'message': f'User {user.username} activated successfully.'})


@api_view(['POST'])
@permission_classes([permissions.IsAdminUser])
def deactivate_user_view(request, user_id):
    """Deactivate a user (admin only)."""
    user = get_object_or_404(User, id=user_id)
    
    if user.is_superuser:
        return Response(
            {'error': 'Cannot deactivate superuser.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user.is_active = False
    user.save()
    
    return Response({'message': f'User {user.username} deactivated successfully.'})
