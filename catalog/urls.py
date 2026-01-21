from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    path('', views.index, name='index'),
    path('biblioteca/', views.biblioteca, name='biblioteca'),
    path('platform/<slug:slug>/data', views.biblioteca_data, name='biblioteca_data'),
    path('title/<int:title_id>/detail', views.title_detail, name='title_detail'),
]
