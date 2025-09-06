import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from rest_framework.test import APIClient

from apps.catalog.models import Category, Product

User = get_user_model()


@pytest.fixture(autouse=True)
def _clear_cache():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def user(db):
    return User.objects.create_user(username="u1", password="pass")


@pytest.fixture
def other_user(db):
    return User.objects.create_user(username="u2", password="pass")


@pytest.fixture
def admin_user(db):
    return User.objects.create_user(username="admin", password="admin", is_staff=True, is_superuser=True)


@pytest.fixture
def api_client(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


@pytest.fixture
def other_client(other_user):
    client = APIClient()
    client.force_authenticate(other_user)
    return client


@pytest.fixture
def admin_client(admin_user):
    client = APIClient()
    client.force_authenticate(admin_user)
    return client


@pytest.fixture
def category(db):
    return Category.objects.create(name="Electronics", slug="electronics", is_active=True)


@pytest.fixture
def products(category):
    """Два активных товара с запасом на складе."""
    p1 = Product.objects.create(name="Phone", description="d", price=500, stock=10, category=category, is_active=True)
    p2 = Product.objects.create(name="Case", description="d", price=20, stock=50, category=category, is_active=True)
    return p1, p2
