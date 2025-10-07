from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import LocationViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'', LocationViewSet, basename='location')

app_name = 'storage_location'
urlpatterns = router.urls
