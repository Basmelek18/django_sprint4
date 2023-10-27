import datetime

from django.shortcuts import render, get_object_or_404

from blog.models import Post, Category

NUMBER_OF_POSTS = 5


def get_post_queryset():
    return Post.objects.select_related(
        'category',
        'author',
        'location'
    ).filter(
        pub_date__date__lt=datetime.datetime.now(),
        is_published=True,
        category__is_published=True
    )


def index(request):
    template = 'blog/index.html'
    post_list = get_post_queryset()[:NUMBER_OF_POSTS]
    context = {'post_list': post_list}
    return render(request, template, context)


def post_detail(request, post_id):
    template = 'blog/detail.html'
    post = get_object_or_404(get_post_queryset(), pk=post_id)
    context = {'post': post}
    return render(request, template, context)


def category_posts(request, category_slug):
    template = 'blog/category.html'
    category = get_object_or_404(
        Category,
        slug=category_slug,
        is_published=True
    )
    post_list = get_post_queryset().filter(category__slug=category_slug)
    context = {
        'category': category,
        'post_list': post_list
    }
    return render(request, template, context)
