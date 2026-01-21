from django.core.management.base import BaseCommand
from catalog.models import Platform, Genre, Title


class Command(BaseCommand):
    help = 'Load sample platforms, genres and titles (Argentina)'

    def handle(self, *args, **options):
        # create platforms
        netflix, _ = Platform.objects.get_or_create(name='Netflix', defaults={'image_url': 'https://via.placeholder.com/300x150?text=Netflix'})
        prime, _ = Platform.objects.get_or_create(name='Prime Video', defaults={'image_url': 'https://via.placeholder.com/300x150?text=Prime'})
        disney, _ = Platform.objects.get_or_create(name='Disney+', defaults={'image_url': 'https://via.placeholder.com/300x150?text=Disney+'})

        # genres
        action, _ = Genre.objects.get_or_create(name='Acción', defaults={'slug': 'accion'})
        drama, _ = Genre.objects.get_or_create(name='Drama', defaults={'slug': 'drama'})
        comedy, _ = Genre.objects.get_or_create(name='Comedia', defaults={'slug': 'comedia'})

        # titles sample
        t1, _ = Title.objects.get_or_create(platform=netflix, title='Película de Acción AR', defaults={'type': 'movie', 'popularity': 80, 'description': 'Una peli de acción disponible en Argentina', 'poster_url': 'https://via.placeholder.com/200x300?text=Pel+Accion', 'regions': 'AR'})
        t1.genres.set([action])

        t2, _ = Title.objects.get_or_create(platform=prime, title='Serie Dramática', defaults={'type': 'series', 'popularity': 95, 'description': 'Una serie dramática top', 'poster_url': 'https://via.placeholder.com/200x300?text=Serie+Drama', 'regions': 'AR'})
        t2.genres.set([drama])

        t3, _ = Title.objects.get_or_create(platform=disney, title='Comedia Familiar', defaults={'type': 'movie', 'popularity': 60, 'description': 'Comedia para toda la familia', 'poster_url': 'https://via.placeholder.com/200x300?text=Comedia', 'regions': 'AR'})
        t3.genres.set([comedy])

        self.stdout.write(self.style.SUCCESS('Sample data loaded.'))
