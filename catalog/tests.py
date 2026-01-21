from django.test import TestCase
from django.urls import reverse
from .models import Platform, Title, Genre


class CatalogViewsTest(TestCase):
    def setUp(self):
        p = Platform.objects.create(name='TestPlat')
        g = Genre.objects.create(name='TestGen', slug='testgen')
        t = Title.objects.create(platform=p, title='Test Movie AR', type='movie', popularity=10, regions='AR')
        t.genres.add(g)

    def test_index(self):
        resp = self.client.get(reverse('catalog:index'))
        self.assertEqual(resp.status_code, 200)

    def test_platform_library(self):
        p = Platform.objects.first()
        resp = self.client.get(reverse('catalog:platform_library', args=[p.slug]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Test Movie AR')
