from rest_framework.routers import DefaultRouter
from .view import UserViewSet

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='users')

# Expose urlpatterns for tests that import it directly
urlpatterns = router.urls
