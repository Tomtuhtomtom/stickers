from django.shortcuts import render, get_object_or_404
from rest_framework import generics, status
from stickers.permissions import IsCreatorOrReadOnly, IsUserOrReadOnly
from .models import Sticker, CustomUser, Follow
from .serializers import StickerListSerializer, UserSerializer, FollowSerializer, FollowingListSerializer, FollowerListSerializer
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.reverse import reverse
from django.db import IntegrityError
from rest_framework.serializers import ValidationError
from rest_framework import filters


@api_view(['GET'])
def api_root(request, format=None):
    return Response({
        'stickers/': reverse('all-stickers', request=request, format=format),
    })


class StickerList(generics.ListCreateAPIView):
    queryset = Sticker.objects.all().order_by('-created_at')
    serializer_class = StickerListSerializer
    permission_classes = []
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['-created_at', 'creator']

    def perform_create(self, serializer):
        try:
            serializer.save(creator=self.request.user)
        except IntegrityError:
            raise ValidationError({"error": "Sticker title already exists"})


class UserStickerList(generics.ListCreateAPIView):
    queryset = Sticker.objects.all()
    serializer_class = StickerListSerializer
    permission_classes = []
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'title']

    def get_queryset(self):
        user = get_object_or_404(CustomUser, pk=self.kwargs['pk'])
        queryset = user.stickers.all().order_by('-created_at')
        return queryset.order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)


class MyStickerList(generics.ListCreateAPIView):
    serializer_class = StickerListSerializer
    permission_classes = []
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'title']

    def perform_create(self, serializer):
        serializer.save(creator=self.request.user)

    def get_queryset(self):
        queryset = self.request.user.stickers.all()
        return queryset.order_by('-created_at')


class FollowListStickers(generics.ListAPIView):
    queryset = Sticker.objects.none()
    serializer_class = StickerListSerializer
    permission_classes = ()
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['created_at', 'username', 'display_name']

    def get_queryset(self):
        queryset = super().get_queryset().order_by('-created_at')
        list_of_followed_users = Follow.objects.filter(
            following_user=self.request.user)
        for user in list_of_followed_users:
            stickers = Sticker.objects.filter(creator=user.followed_user)
            queryset = queryset | stickers
        return queryset.order_by('-created_at')


class StickerDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Sticker.objects.all()
    serializer_class = StickerListSerializer
    permission_classes = [IsCreatorOrReadOnly, ]


class UserList(generics.ListAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = ()
    filter_backends = [filters.OrderingFilter]
    ordering_fields = ['id', 'username']


class UserProfile(generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsUserOrReadOnly, ]

    def get_object(self):
        return self.request.user


class UserDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = CustomUser.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsUserOrReadOnly, ]


# List of User's logged in user is following
class FollowingList(generics.ListAPIView):
    queryset = Follow.objects.all()
    serializer_class = FollowingListSerializer
    permission_classes = ()

    def get_queryset(self):
        user_username = self.request.user.username
        user = get_object_or_404(CustomUser, username=user_username)
        users_following = user.following.all()
        return users_following


class FollowedByList(generics.ListAPIView):
    queryset = Follow.objects.all()
    serializer_class = FollowerListSerializer
    permission_classes = ()

    def get_queryset(self):
        user_username = self.request.user.username
        user = get_object_or_404(CustomUser, username=user_username)
        users_following = user.followed_by.all()
        return users_following


class FollowCreate(generics.ListCreateAPIView):
    queryset = Follow.objects.all()
    serializer_class = FollowSerializer
    permission_classes = ()

    def perform_create(self, serializer):
        user_to_follow = get_object_or_404(CustomUser, pk=self.kwargs['pk'])
        user = self.request.user
        try:
            serializer.save(followed_user=user_to_follow, following_user=user)
        except IntegrityError:
            raise ValidationError({"error": "Already following this user"})


class UnFollowDestroy(generics.RetrieveDestroyAPIView):
    queryset = Follow.objects.all()
    serializer_class = FollowSerializer
    permission_classes = ()

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        user_to_unfollow = self.kwargs['pk']
        follow_instance = Follow.objects.filter(
            followed_user=user_to_unfollow).first().id
        follow_kwargs = {}
        follow_kwargs['pk'] = follow_instance
        lookup_url_kwarg = self.lookup_url_kwarg or self.lookup_field
        assert lookup_url_kwarg in follow_kwargs, (
            'Expected view %s to be called with a URL keyword argument '
            'named "%s". Fix your URL conf, or set the `.lookup_field` '
            'attribute on the view correctly.' %
            (self.__class__.__name__, lookup_url_kwarg)
        )
        filter_kwargs = {self.lookup_field: follow_kwargs[lookup_url_kwarg]}
        obj = get_object_or_404(queryset, **filter_kwargs)
        self.check_object_permissions(self.request, obj)
        return obj

    def destroy(self, request, *args, **kwargs):
        follow_instance = self.get_object()
        try:
            self.perform_destroy(follow_instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except IntegrityError:
            raise ValidationError({"error": "You are not following this user"})
