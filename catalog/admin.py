from django.contrib import admin
from .models import Platform, Genre, Title
from django.contrib import messages
from django.urls import path, reverse
from django.shortcuts import redirect
from django.utils.safestring import mark_safe
from . import tmdb


@admin.register(Platform)
class PlatformAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'tmdb_provider_id', 'admin_actions')
    actions = ['refresh_movies_from_tmdb', 'refresh_series_from_tmdb']

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('<path:object_id>/generate/', self.admin_site.admin_view(self.generate_view), name='catalog_platform_generate'),
            path('<path:object_id>/update/', self.admin_site.admin_view(self.update_view), name='catalog_platform_update'),
            path('<path:object_id>/delete_data/', self.admin_site.admin_view(self.delete_view), name='catalog_platform_delete'),
        ]
        return my_urls + urls

    def admin_actions(self, obj):
        gen_movies = reverse('admin:catalog_platform_generate', args=[obj.pk]) + '?kind=movies'
        gen_series = reverse('admin:catalog_platform_generate', args=[obj.pk]) + '?kind=series'
        upd_movies = reverse('admin:catalog_platform_update', args=[obj.pk]) + '?kind=movies'
        upd_series = reverse('admin:catalog_platform_update', args=[obj.pk]) + '?kind=series'
        del_movies = reverse('admin:catalog_platform_delete', args=[obj.pk]) + '?kind=movies'
        del_series = reverse('admin:catalog_platform_delete', args=[obj.pk]) + '?kind=series'
        html = (
            f"<a class=\"button\" href=\"{gen_movies}\">Gen M</a> "
            f"<a class=\"button\" href=\"{gen_series}\">Gen S</a> "
            f"<a class=\"button\" href=\"{upd_movies}\">Upd M</a> "
            f"<a class=\"button\" href=\"{upd_series}\">Upd S</a> "
            f"<a class=\"button\" href=\"{del_movies}\">Del M</a> "
            f"<a class=\"button\" href=\"{del_series}\">Del S</a>"
        )
        return mark_safe(html)

    admin_actions.short_description = 'Actions'

    def refresh_movies_from_tmdb(self, request, queryset):
        for platform in queryset:
            try:
                path, count = tmdb.generate_platform(platform, kind='movies')
                self.message_user(request, f"Generated movies for {platform.name}: {count} items saved to {path}")
            except Exception as e:
                self.message_user(request, f"Error generating {platform.name}: {e}", level=messages.ERROR)

    refresh_movies_from_tmdb.short_description = 'Refresh movies from TMDB and save JSON'

    def refresh_series_from_tmdb(self, request, queryset):
        for platform in queryset:
            try:
                path, count = tmdb.generate_platform(platform, kind='series')
                self.message_user(request, f"Generated series for {platform.name}: {count} items saved to {path}")
            except Exception as e:
                self.message_user(request, f"Error generating {platform.name}: {e}", level=messages.ERROR)

    refresh_series_from_tmdb.short_description = 'Refresh series from TMDB and save JSON'

    # Admin custom views
    def generate_view(self, request, object_id):
        obj = self.get_object(request, object_id)
        kind = request.GET.get('kind', 'movies')
        try:
            path, count = tmdb.generate_platform(obj, kind=kind)
            self.message_user(request, f"Generated {kind} for {obj.name}: {count} items saved to {path}")
        except Exception as e:
            self.message_user(request, f"Error: {e}", level=messages.ERROR)
        return redirect(request.META.get('HTTP_REFERER', '..'))

    def update_view(self, request, object_id):
        obj = self.get_object(request, object_id)
        kind = request.GET.get('kind', 'movies')
        try:
            path, count = tmdb.update_platform(obj, kind=kind)
            self.message_user(request, f"Updated {kind} for {obj.name}: {count} new items saved to {path}")
        except Exception as e:
            self.message_user(request, f"Error: {e}", level=messages.ERROR)
        return redirect(request.META.get('HTTP_REFERER', '..'))

    def delete_view(self, request, object_id):
        obj = self.get_object(request, object_id)
        kind = request.GET.get('kind', 'movies')
        try:
            removed = tmdb.delete_platform_data(obj, kind=kind)
            msg = f"Deleted {kind} data for {obj.name}. JSON removed: {removed}"
            self.message_user(request, msg)
        except Exception as e:
            self.message_user(request, f"Error: {e}", level=messages.ERROR)
        return redirect(request.META.get('HTTP_REFERER', '..'))


@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')


@admin.register(Title)
class TitleAdmin(admin.ModelAdmin):
    list_display = ('title', 'platform', 'type', 'popularity')
    list_filter = ('type', 'platform')
    search_fields = ('title',)
