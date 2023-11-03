import datetime
import pytz

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from blog.models import Post, Category, User, Comment
from blog.forms import PostForm, UserForm, CommentForm


MAX_NUM_PAGES = 10


def get_post_queryset(filter_on=True, annotate_on=True):
    queryset = Post.objects.select_related(
        'category',
        'author',
        'location',
    )
    if filter_on:
        queryset = queryset.filter(
            pub_date__date__lt=datetime.datetime.now(),
            is_published=True,
            category__is_published=True
        )
    if annotate_on:
        queryset = queryset.annotate(
            comment_count=Count('comment')
        ).order_by('-pub_date')
    return queryset


def index(request):
    template = 'blog/index.html'
    page_obj = Paginator(get_post_queryset(),
                         MAX_NUM_PAGES).get_page(request.GET.get('page'))
    context = {'page_obj': page_obj}
    return render(request, template, context)


def post_detail(request, post_id):
    template = 'blog/detail.html'
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user and (
            not post.is_published
            or not post.category.is_published
            or post.pub_date >= pytz.utc.localize(datetime.datetime.now())
    ):
        raise Http404()
    context = {'post': post,
               'form': CommentForm(),
               'comments': post.comment.select_related('author')}

    return render(request, template, context)


def category_posts(request, category_slug):
    template = 'blog/category.html'
    category = get_object_or_404(
        Category,
        slug=category_slug,
        is_published=True
    )
    page_obj = Paginator(get_post_queryset().filter(
        category__slug=category_slug
    ), MAX_NUM_PAGES).get_page(request.GET.get('page'))
    context = {
        'category': category,
        'page_obj': page_obj
    }
    return render(request, template, context)


class PostDispatchMixin:

    def dispatch(self, request, *args, **kwargs):
        self.instance = get_object_or_404(Post, pk=kwargs.get('post_id'))
        if self.instance.author != request.user:
            return redirect('blog:post_detail', post_id=kwargs.get('post_id'))
        return super().dispatch(request, *args, **kwargs)


class PostSuccessMixin:

    def get_success_url(self):
        return reverse(
            'blog:profile',
            kwargs={'username': self.request.user}
        )


class CommentMixin:
    model = Comment
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'

    def dispatch(self, request, *args, **kwargs):
        self.instance = get_object_or_404(
            Comment,
            pk=kwargs.get('comment_id'),
            post_id=kwargs.get('post_id')
        )
        if self.instance.author != request.user:
            return redirect('blog:post_detail', post_id=kwargs.get('post_id'))
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse(
            'blog:post_detail',
            kwargs={'post_id': self.instance.post_id}
        )


class UserListView(ListView):
    model = Post
    template_name = 'blog/profile.html'
    context_object_name = 'post_list'
    paginate_by = MAX_NUM_PAGES

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = self.profile
        return context

    def get_queryset(self):
        self.profile = get_object_or_404(
            User,
            username=self.kwargs['username']
        )
        if self.profile.username == str(self.request.user):
            queryset = get_post_queryset(False, True)
        elif self.profile.username != self.request.user:
            queryset = get_post_queryset(True, True)
        return queryset.filter(author=self.profile)


class UserUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserForm
    template_name = 'blog/user.html'

    def get_object(self, queryset=None):
        queryset = User.objects.filter(username=self.request.user)
        return queryset.get()

    def get_success_url(self):
        return reverse('blog:profile', kwargs={'username': self.request.user})


class PostUpdateView(LoginRequiredMixin, PostDispatchMixin, UpdateView):
    model = Post
    form_class = PostForm
    pk_url_kwarg = 'post_id'
    template_name = 'blog/create.html'

    def get_success_url(self):
        return reverse(
            'blog:post_detail',
            kwargs={'post_id': self.instance.pk}
        )


class PostCreateView(LoginRequiredMixin, PostSuccessMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)


class PostDeleteView(
    LoginRequiredMixin, PostDispatchMixin, PostSuccessMixin, DeleteView
):
    model = Post
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = {'instance': self.instance}
        return context


class CommentCreateView(LoginRequiredMixin, CreateView):
    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment.html'

    def dispatch(self, request, *args, **kwargs):
        self.poster = get_object_or_404(Post, pk=kwargs['post_id'])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.author = self.request.user
        form.instance.post = self.poster
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            'blog:post_detail',
            kwargs={'post_id': self.poster.pk}
        )


class CommentUpdateView(LoginRequiredMixin, CommentMixin, UpdateView):
    form_class = CommentForm

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)


class CommentDeleteView(LoginRequiredMixin, CommentMixin, DeleteView):
    pass
