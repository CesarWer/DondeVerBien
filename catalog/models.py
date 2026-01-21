from django.db import models
from django.utils.text import slugify


class Platform(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True)
    image_url = models.URLField(blank=True)
    # Optional TMDB provider id (useful to discover titles available on a provider)
    tmdb_provider_id = models.IntegerField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Genre(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True)

    def __str__(self):
        return self.name


class Title(models.Model):
    TYPE_CHOICES = (
        ('movie', 'Película'),
        ('series', 'Serie'),
    )

    platform = models.ForeignKey(Platform, on_delete=models.CASCADE, related_name='titles')
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, blank=True)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    genres = models.ManyToManyField(Genre, blank=True)
    popularity = models.IntegerField(default=0)
    description = models.TextField(blank=True)
    poster_url = models.URLField(blank=True)
    # simple region code storage; include 'AR' for Argentina
    regions = models.CharField(max_length=200, default='AR')
    # TMDB id for the title (movie or tv). Use to avoid duplicates when syncing.
    tmdb_id = models.IntegerField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)

    def available_in_argentina(self):
        regs = [r.strip().upper() for r in (self.regions or '').split(',') if r.strip()]
        return 'AR' in regs

    def __str__(self):
        return f"{self.title} ({self.get_type_display()})"

    class Meta:
        unique_together = (('platform', 'tmdb_id'),)
