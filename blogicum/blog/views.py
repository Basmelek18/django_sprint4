import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Count
from django.http import Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView

from blog.models import Post, Category, User, Comment
from blog.forms import PostForm, UserForm, CommentForm


MAX_NUM_PAGES = 10


def get_post_queryset():
    return Post.objects.select_related(
        'category',
        'author',
        'location',
    ).filter(
        pub_date__date__lt=datetime.datetime.now(),
        is_published=True,
        category__is_published=True
    ).annotate(comment_count=Count('comment')).order_by('-pub_date')


def index(request):
    template = 'blog/index.html'
    page_obj = Paginator(get_post_queryset(),
                         MAX_NUM_PAGES).get_page(request.GET.get('page'))
    context = {'page_obj': page_obj}
    return render(request, template, context)


def post_detail(request, post_id):
    template = 'blog/detail.html'
    post = get_object_or_404(Post, pk=post_id)
    if post.author != request.user and not post.is_published:
        post = get_object_or_404(get_post_queryset(), pk=post_id)
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
        category__slug=category_slug), MAX_NUM_PAGES).get_page(request.GET.get('page'))
    context = {
        'category': category,
        'page_obj': page_obj
    }
    return render(request, template, context)


class UserListView(ListView):
    model = Post
    template_name = 'blog/profile.html'
    context_object_name = 'post_list'
    paginate_by = MAX_NUM_PAGES

    def get_author(self):
        return get_object_or_404(User, username=self.kwargs['username'])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['profile'] = self.get_author()
        return context

    def get_queryset(self):
        return Post.objects.filter(author=self.get_author()).annotate(
            comment_count=Count('comment')).order_by('-pub_date')


class UserUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserForm
    template_name = 'blog/user.html'
    slug_field = 'username'
    slug_url_kwarg = 'username'

    def get_author(self):
        return get_object_or_404(User, username=self.kwargs['username'])

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()

        slug = self.kwargs.get(self.slug_url_kwarg)
        slug_field = self.get_slug_field()
        queryset = queryset.filter(**{slug_field: slug})
        obj = queryset.get()

        return obj

    def get_success_url(self):
        return reverse('blog:profile', kwargs={'username': self.get_author()})

    def dispatch(self, request, *args, **kwargs):
        if request.user == self.get_author():
            return super().dispatch(request, *args, **kwargs)
        else:
            raise Http404()


class PostUpdateView(LoginRequiredMixin, UpdateView):
    model = Post
    form_class = PostForm
    pk_url_kwarg = 'post_id'
    template_name = 'blog/create.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def dispatch(self, request, *args, **kwargs):
        self.instance = get_object_or_404(Post, pk=kwargs.get('post_id'))
        if self.instance.author != request.user:
            return redirect('blog:post_detail', post_id=kwargs.get('post_id'))
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'post_id': self.instance.pk})


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('blog:profile', kwargs={'username': self.object.author})


class PostDeleteView(DeleteView):
    model = Post
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'

    def dispatch(self, request, *args, **kwargs):
        self.instance = get_object_or_404(Post, pk=kwargs.get('post_id'))
        if self.instance.author != request.user:
            return redirect('blog:post_detail', post_id=kwargs.get('post_id'))
        return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse('blog:profile', kwargs={'username': self.object.author})


class CommentCreateView(LoginRequiredMixin, CreateView):
    poster = None
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
        return reverse('blog:post_detail', kwargs={'post_id': self.poster.pk})


class CommentUpdateView(LoginRequiredMixin, UpdateView):
    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            get_object_or_404(Comment, pk=kwargs['comment_id'], author=request.user)
            return super().dispatch(request, *args, **kwargs)
        else:
            return redirect('blog:post_detail', post_id=kwargs.get('post_id'))

    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'post_id': self.object.post.pk})


class CommentDeleteView(LoginRequiredMixin, DeleteView):
    model = Comment
    template_name = 'blog/comment.html'
    success_url = reverse_lazy('blog:index')
    pk_url_kwarg = 'comment_id'

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            get_object_or_404(Comment, pk=kwargs['comment_id'], author=request.user)
            return super().dispatch(request, *args, **kwargs)
        else:
            return redirect('blog:post_detail', post_id=kwargs.get('post_id'))

    def get_success_url(self):
        return reverse('blog:post_detail', kwargs={'post_id': self.object.post.pk})
