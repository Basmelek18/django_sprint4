from django.urls import path, reverse_lazy

from . import views

app_name = 'blog'
pk_url_kwarg = 'post_id'

urlpatterns = [
    path('', views.index, name='index'),
    path(
        'posts/<int:post_id>/',
        views.post_detail,
        name='post_detail'
    ),
    path(
        'category/<slug:category_slug>/',
        views.category_posts,
        name='category_posts'
    ),
    path('profile/<slug:username>/', views.UserListView.as_view(), name='profile'),
    path('profile/<slug:username>/edit/', views.UserUpdateView.as_view(), name='edit_profile'),
    path('posts/create/', views.PostCreateView.as_view(), name='create_post'),
    path('posts/<int:post_id>/edit/', views.PostUpdateView.as_view(), name='edit_post'),
    path('posts/<int:post_id>/delete/', views.PostDeleteView.as_view(), name='delete'),
]
