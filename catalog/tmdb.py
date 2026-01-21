import os
import requests
from django.conf import settings
from pathlib import Path
from .models import Title, Genre
import time
from django.db import transaction


def get_tmdb_api_key():
    # prefer explicit setting, fall back to environment
    key = getattr(settings, 'TMDB_API_KEY', '') or os.environ.get('TMDB_API_KEY')
    if not key:
        raise RuntimeError('TMDB API key not configured. Set settings.TMDB_API_KEY or env TMDB_API_KEY')
    return key


def tmdb_request(path, params=None):
    base = 'https://api.themoviedb.org/3'
    params = params.copy() if params else {}
    params['api_key'] = get_tmdb_api_key()
    resp = requests.get(f"{base}/{path}", params=params, timeout=20)
    resp.raise_for_status()
    return resp.json()


def discover_movies(provider_id, region='AR', max_pages=5):
    # returns list of movie dicts from TMDB discover endpoint filtered by provider
    results = []
    page = 1
    while page <= max_pages:
        # This matches the Go scraper usage example:
        # https://api.themoviedb.org/3/discover/movie?api_key=API_KEY&with_watch_providers=PROVIDER_ID&watch_region=AR&language=es-ES&page=PAGE
        data = tmdb_request('discover/movie', params={
            'with_watch_providers': provider_id,
            'watch_region': region,
            'page': page,
            # Use Spanish (Spain) like your scraper example; TMDB supports es-ES
            'language': 'es-ES',
        })
        results.extend(data.get('results', []))
        if page >= data.get('total_pages', 0):
            break
        # respect request delay
        time.sleep(getattr(settings, 'TMDB_REQUEST_DELAY', 0.25))
        page += 1
    return results


def discover_tv(provider_id, region='AR', max_pages=5):
    results = []
    page = 1
    while page <= max_pages:
        data = tmdb_request('discover/tv', params={
            'with_watch_providers': provider_id,
            'watch_region': region,
            'page': page,
            'language': 'es-ES',
        })
        results.extend(data.get('results', []))
        if page >= data.get('total_pages', 0):
            break
        time.sleep(getattr(settings, 'TMDB_REQUEST_DELAY', 0.25))
        page += 1
    return results


def get_total_pages(provider_id, kind='movies', region='AR'):
    # Query first page to get total_pages
    endpoint = 'discover/movie' if kind == 'movies' else 'discover/tv'
    data = tmdb_request(endpoint, params={
        'with_watch_providers': provider_id,
        'watch_region': region,
        'page': 1,
        'language': 'es-ES',
    })
    return int(data.get('total_pages', 1)), data.get('results', [])


def fetch_and_sync_genres():
    """Fetch genre lists for movies and tv from TMDB and sync to Genre model."""
    movie = tmdb_request('genre/movie/list', params={'language': 'es-ES'})
    tv = tmdb_request('genre/tv/list', params={'language': 'es-ES'})
    all_genres = []
    for g in movie.get('genres', []):
        all_genres.append(('movie', g))
    for g in tv.get('genres', []):
        all_genres.append(('tv', g))

    created = 0
    for kind, g in all_genres:
        gid = g.get('id')
        name = g.get('name')
        slug = f"tmdb-{gid}"
        obj, was_new = Genre.objects.update_or_create(slug=slug, defaults={'name': name})
        if was_new:
            created += 1
    return created


def _create_or_update_title_from_item(platform, it, kind='movies'):
    # Use TMDB id as unique key when available
    tmdb_id = it.get('id')
    if kind == 'movies':
        title_text = it.get('title') or it.get('original_title')
        t_type = 'movie'
    else:
        title_text = it.get('name') or it.get('original_name')
        t_type = 'series'

    popularity = int(it.get('popularity') or 0)
    description = it.get('overview') or ''
    poster_path = it.get('poster_path')
    poster_url = f"https://image.tmdb.org/t/p/w300{poster_path}" if poster_path else ''

    # use tmdb_id when present
    if tmdb_id:
        t_obj, created = Title.objects.get_or_create(
            platform=platform,
            tmdb_id=tmdb_id,
            defaults={
                'title': title_text,
                'type': t_type,
                'popularity': popularity,
                'description': description,
                'poster_url': poster_url,
                'regions': 'AR',
            }
        )
        if not created:
            t_obj.title = title_text
            t_obj.type = t_type
            t_obj.popularity = popularity
            t_obj.description = description
            t_obj.poster_url = poster_url
            t_obj.regions = 'AR'
            t_obj.save()
    else:
        # fallback to title-based upsert
        t_obj, created = Title.objects.get_or_create(
            platform=platform,
            title=title_text,
            defaults={
                'type': t_type,
                'popularity': popularity,
                'description': description,
                'poster_url': poster_url,
                'regions': 'AR',
            }
        )

    # genres from genre_ids -> map to synced Genre objects when available
    genre_ids = it.get('genre_ids', [])
    if genre_ids:
        genre_objs = []
        for gid in genre_ids:
            slug = f"tmdb-{gid}"
            # if genre exists it will have proper name from fetch_and_sync_genres
            obj, _ = Genre.objects.get_or_create(slug=slug, defaults={'name': f'Genre {gid}'})
            genre_objs.append(obj)
        t_obj.genres.set(genre_objs)

    return t_obj


def generate_platform(platform, kind='movies'):
    """Generate full dataset for platform: delete existing and fetch all pages."""
    pid = platform.tmdb_provider_id
    if not pid:
        raise ValueError('Platform does not have tmdb_provider_id set')

    # sync genres first
    try:
        fetch_and_sync_genres()
    except Exception:
        # non-fatal: continue even if genres can't be synced
        pass

    total_pages, first_page_results = get_total_pages(pid, kind=kind)
    all_items = []
    all_items.extend(first_page_results)

    # fetch remaining pages
    for page in range(2, total_pages + 1):
        endpoint = 'discover/movie' if kind == 'movies' else 'discover/tv'
        data = tmdb_request(endpoint, params={
            'with_watch_providers': pid,
            'watch_region': 'AR',
            'page': page,
            'language': 'es-ES',
        })
        all_items.extend(data.get('results', []))
        time.sleep(getattr(settings, 'TMDB_REQUEST_DELAY', 0.25))

    # delete existing titles for this platform & kind
    Title.objects.filter(platform=platform, type=('movie' if kind == 'movies' else 'series')).delete()

    created_count = 0
    with transaction.atomic():
        for it in all_items:
            _create_or_update_title_from_item(platform, it, kind=kind)
            created_count += 1

    save_path = save_json_for_platform(platform.slug, kind, all_items)
    return save_path, created_count


def update_platform(platform, kind='movies'):
    """Update dataset for platform: fetch all pages and add new items not already present (by tmdb_id)."""
    pid = platform.tmdb_provider_id
    if not pid:
        raise ValueError('Platform does not have tmdb_provider_id set')

    try:
        fetch_and_sync_genres()
    except Exception:
        pass

    total_pages, first_page_results = get_total_pages(pid, kind=kind)
    new_items = []

    # process first page
    pages = [1]
    pages.extend(range(2, total_pages + 1))
    created_count = 0
    all_items = []
    for page in pages:
        endpoint = 'discover/movie' if kind == 'movies' else 'discover/tv'
        data = tmdb_request(endpoint, params={
            'with_watch_providers': pid,
            'watch_region': 'AR',
            'page': page,
            'language': 'es-ES',
        })
        items = data.get('results', [])
        all_items.extend(items)
        for it in items:
            tmdb_id = it.get('id')
            exists = False
            if tmdb_id:
                exists = Title.objects.filter(platform=platform, tmdb_id=tmdb_id).exists()
            else:
                # fallback: check by title
                title_text = it.get('title') or it.get('name') or it.get('original_title') or it.get('original_name')
                exists = Title.objects.filter(platform=platform, title=title_text).exists()
            if not exists:
                _create_or_update_title_from_item(platform, it, kind=kind)
                created_count += 1

        time.sleep(getattr(settings, 'TMDB_REQUEST_DELAY', 0.25))

    save_path = save_json_for_platform(platform.slug, kind, all_items)
    return save_path, created_count


def delete_platform_data(platform, kind='movies'):
    # delete DB entries and JSON file
    Title.objects.filter(platform=platform, type=('movie' if kind == 'movies' else 'series')).delete()
    base = Path(settings.BASE_DIR)
    fname = base / 'data' / f"{platform.slug}-{kind}.json"
    if fname.exists():
        fname.unlink()
        removed = True
    else:
        removed = False
    return removed


def ensure_genres(tmdb_genre_list):
    # tmdb_genre_list is list of dicts or ids; we accept dicts with 'name' or simple names
    created = []
    for g in tmdb_genre_list:
        name = g.get('name') if isinstance(g, dict) else str(g)
        slug = name.lower().replace(' ', '-')
        obj, _ = Genre.objects.get_or_create(slug=slug, defaults={'name': name})
        created.append(obj)
    return created


def save_json_for_platform(platform_slug, kind, data):
    # kind: 'movies' or 'series'
    base = Path(settings.BASE_DIR)
    outdir = base / 'data'
    outdir.mkdir(exist_ok=True)
    fname = outdir / f"{platform_slug}-{kind}.json"
    with open(fname, 'w', encoding='utf-8') as fh:
        import json
        json.dump(data, fh, ensure_ascii=False, indent=2)
    return str(fname)


def refresh_platform_from_tmdb(platform, kind='movies'):
    """Fetch movies or tv for a Platform (requires platform.tmdb_provider_id) and save JSON and update DB titles."""
    pid = platform.tmdb_provider_id
    if not pid:
        raise ValueError('Platform does not have tmdb_provider_id set')
    if kind == 'movies':
        items = discover_movies(pid)
    else:
        items = discover_tv(pid)

    # Save raw JSON
    save_path = save_json_for_platform(platform.slug, kind, items)

    # Upsert into Titles (basic mapping)
    for it in items:
        if kind == 'movies':
            title_text = it.get('title') or it.get('original_title')
            t_type = 'movie'
            genre_objs = []
            # TMDB returns 'genre_ids' here; we'll ignore ids and only use genre names when available
            # try to fetch genre names if present in item
            # The item may contain 'genre_ids' only; for now we'll create Genre objects using ids as names
            genre_ids = it.get('genre_ids', [])
            genre_objs = []
            for gid in genre_ids:
                name = f'genre-{gid}'
                obj, _ = Genre.objects.get_or_create(slug=str(gid), defaults={'name': name})
                genre_objs.append(obj)
        else:
            title_text = it.get('name') or it.get('original_name')
            t_type = 'series'
            genre_ids = it.get('genre_ids', [])
            genre_objs = []
            for gid in genre_ids:
                name = f'genre-{gid}'
                obj, _ = Genre.objects.get_or_create(slug=str(gid), defaults={'name': name})
                genre_objs.append(obj)

        popularity = int(it.get('popularity') or 0)
        description = it.get('overview') or ''
        poster_path = it.get('poster_path')
        poster_url = f"https://image.tmdb.org/t/p/w300{poster_path}" if poster_path else ''

        # create or update
        t_obj, created = Title.objects.get_or_create(
            platform=platform,
            title=title_text,
            defaults={
                'type': t_type,
                'popularity': popularity,
                'description': description,
                'poster_url': poster_url,
                'regions': 'AR',
            }
        )
        if not created:
            t_obj.type = t_type
            t_obj.popularity = popularity
            t_obj.description = description
            t_obj.poster_url = poster_url
            t_obj.regions = 'AR'
            t_obj.save()
        if genre_objs:
            t_obj.genres.set(genre_objs)

    return save_path, len(items)
