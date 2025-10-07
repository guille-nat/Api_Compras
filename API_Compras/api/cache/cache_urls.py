from django.urls import path
from api.cache import cache_views as cache_views

urlpatterns = [
    path('stats', cache_views.get_cache_stats, name='cache_stats'),
    path('clear-pattern', cache_views.clear_cache_pattern,
         name='clear_cache_pattern'),
    path('clear-all', cache_views.clear_all_cache, name='clear_all_cache'),
    path('warm-up', cache_views.warm_up_cache, name='warm_up_cache'),
]
