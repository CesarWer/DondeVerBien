from django.shortcuts import render, get_object_or_404
from .models import Platform, Title, Genre
from django.db.models import Q
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.template.loader import render_to_string
from django.http import JsonResponse


def _apply_genre_filter_and(qs, selected_genres):
    """
    Apply AND logic to genre filtering: only return titles that have ALL selected genres.
    """
    if not selected_genres:
        return qs
    
    for genre_slug in selected_genres:
        qs = qs.filter(genres__slug=genre_slug).distinct()
    
    return qs


def index(request):
    platforms = list(Platform.objects.all())
    # compute a resolved logo URL for each platform (prefer local static files)
    from django.conf import settings
    from pathlib import Path
    for p in platforms:
        svg_path = Path(settings.BASE_DIR) / 'static' / 'logos' / f"{p.slug}.svg"
        png_path = Path(settings.BASE_DIR) / 'static' / 'logos' / f"{p.slug}.png"
        if svg_path.exists():
            p.logo_url = f"/static/logos/{p.slug}.svg"
        elif png_path.exists():
            p.logo_url = f"/static/logos/{p.slug}.png"
        elif p.image_url:
            p.logo_url = p.image_url
        else:
            p.logo_url = ''

    return render(request, 'catalog/index.html', {'platforms': platforms})


def biblioteca(request):
    """
    Unified library view. Accepts optional 'platforms' query parameter (multiple).
    - No platforms param or empty: show all platforms
    - With platforms param: show only those platforms
    """
    supported_platforms = Platform.objects.all()
    all_slugs = [p.slug for p in supported_platforms]
    
    # Get the selected platforms from query params (can be multiple)
    selected_platforms_param = request.GET.getlist('platforms')
    
    if selected_platforms_param:
        # Filter to valid platforms only
        selected_platforms = [p for p in selected_platforms_param if p in all_slugs]
        if not selected_platforms:
            selected_platforms = all_slugs
    else:
        # No platform param: show all
        selected_platforms = all_slugs
    
    current_platform = supported_platforms.filter(slug__in=selected_platforms).first() or supported_platforms.first()
    
    # Base queryset
    qs = Title.objects.filter(platform__slug__in=selected_platforms, regions__icontains='AR').distinct()
    
    # search
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
    
    # type filters
    selected_types = request.GET.getlist('type')
    if selected_types:
        qs = qs.filter(type__in=selected_types)
    
    # genres (AND logic: title must have ALL selected genres)
    selected_genres = request.GET.getlist('genre')
    if selected_genres:
        qs = _apply_genre_filter_and(qs, selected_genres)
    
    # sorting
    sort = request.GET.get('sort')
    if sort == 'pop_asc':
        qs = qs.order_by('popularity')
    elif sort == 'pop_desc':
        qs = qs.order_by('-popularity')
    else:
        qs = qs.order_by('-popularity')
    
    # pagination
    try:
        page_size = int(request.GET.get('page_size', 25))
    except ValueError:
        page_size = 25
    if page_size not in (25, 50, 100):
        page_size = 25
    
    paginator = Paginator(qs, page_size)
    page = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    # genres with counts
    genres = Genre.objects.order_by('name')
    genres_with_counts = []
    for g in genres:
        count = Title.objects.filter(platform__slug__in=selected_platforms, regions__icontains='AR', genres=g).count()
        if count > 0:
            genres_with_counts.append({'slug': g.slug, 'name': g.name, 'count': count})
    
    # Determine header text
    is_all_platforms = len(selected_platforms) == len(all_slugs)
    
    context = {
        'platform': current_platform,
        'supported_platforms': supported_platforms,
        'selected_platforms': selected_platforms,
        'selected_platform_names': [p.name for p in supported_platforms if p.slug in selected_platforms],
        'page_obj': page_obj,
        'paginator': paginator,
        'page_size': page_size,
        'page_sizes': [25, 50, 100],
        'genres_with_counts': genres_with_counts,
        'selected_genres': selected_genres,
        'selected_types': selected_types,
        'q': q,
        'sort': sort,
        'is_all_platforms': is_all_platforms,
    }
    return render(request, 'catalog/biblioteca.html', context)


def biblioteca_data(request, slug):
    """
    AJAX endpoint for biblioteca. Accepts multiple 'platforms' params via GET.
    Returns JSON with titles_html and genres_html.
    """
    supported_platforms = Platform.objects.all()
    all_slugs = [p.slug for p in supported_platforms]
    
    # Get selected platforms from query param (can be multiple)
    selected_platforms_param = request.GET.getlist('platforms')
    
    if selected_platforms_param:
        selected_platforms = [p for p in selected_platforms_param if p in all_slugs]
        if not selected_platforms:
            selected_platforms = all_slugs
    else:
        selected_platforms = all_slugs
    
    current_platform = supported_platforms.filter(slug__in=selected_platforms).first() or supported_platforms.first()
    
    # Reuse biblioteca logic
    qs = Title.objects.filter(platform__slug__in=selected_platforms, regions__icontains='AR').distinct()
    
    q = request.GET.get('q', '').strip()
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(description__icontains=q))
    
    selected_types = request.GET.getlist('type')
    if selected_types:
        qs = qs.filter(type__in=selected_types)
    
    selected_genres = request.GET.getlist('genre')
    if selected_genres:
        qs = _apply_genre_filter_and(qs, selected_genres)
    
    sort = request.GET.get('sort')
    if sort == 'pop_asc':
        qs = qs.order_by('popularity')
    elif sort == 'pop_desc':
        qs = qs.order_by('-popularity')
    else:
        qs = qs.order_by('-popularity')
    
    try:
        page_size = int(request.GET.get('page_size', 25))
    except ValueError:
        page_size = 25
    if page_size not in (25, 50, 100):
        page_size = 25
    
    paginator = Paginator(qs, page_size)
    page = request.GET.get('page', 1)
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    
    # genres
    genres = Genre.objects.order_by('name')
    genres_with_counts = []
    for g in genres:
        count = Title.objects.filter(platform__slug__in=selected_platforms, regions__icontains='AR', genres=g).count()
        if count > 0:
            genres_with_counts.append({'slug': g.slug, 'name': g.name, 'count': count})
    
    is_all_platforms = len(selected_platforms) == len(all_slugs)
    
    titles_context = {
        'page_obj': page_obj,
        'paginator': paginator,
        'platform': current_platform,
        'selected_platforms': selected_platforms,
        'selected_platform_names': [p.name for p in supported_platforms if p.slug in selected_platforms],
        'is_all_platforms': is_all_platforms,
    }
    genres_context = {
        'genres_with_counts': genres_with_counts,
        'selected_genres': selected_genres,
    }
    
    titles_html = render_to_string('catalog/_titles_grid.html', titles_context, request=request)
    genres_html = render_to_string('catalog/_genres_list.html', genres_context, request=request)
    
    return JsonResponse({'titles_html': titles_html, 'genres_html': genres_html})


def title_detail(request, title_id):
    """
    AJAX endpoint to get details of a single title.
    Returns JSON with HTML of the title detail card.
    """
    title = get_object_or_404(Title, id=title_id)
    
    context = {
        'title': title,
    }
    
    detail_html = render_to_string('catalog/_title_detail.html', context, request=request)
    
    return JsonResponse({'detail_html': detail_html})
