import hashlib
from random import random
from urllib.parse import urlencode
from django.core.cache import cache

from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404
from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework.views import APIView
from rest_framework import filters
from apps.catalog.models import Category, Product
from apps.catalog.serializers import CategoryListSerializer, ProductListSerializer
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page


def _ttl_with_jitter(base: int = 300, jitter: float = 0.10) -> int:
    """TTL c анти-догпайлом: +-10% по умолчанию."""
    delta = int(base * jitter)
    return base + random.randint(-delta, delta)


def _hash_params(params: dict) -> str:
    """Стабильный хэш нормализованных параметров запроса."""
    encoded = urlencode(sorted(params.items()), doseq=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class AnonCatalogThrottle(AnonRateThrottle):
    rate = "60/min"


class UserCatalogThrottle(UserRateThrottle):
    rate = "240/min"


class CategoryListView(generics.ListAPIView):
    """
    - Только активные категории.
    - Поиск по name (?search=...).
    - Ручной кэш: ключ учитывает параметры поиска.
    - Заголовок X-Cache: HIT|MISS.
    """
    serializer_class = CategoryListSerializer
    throttle_classes = [AnonCatalogThrottle, UserCatalogThrottle]
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']
    pagination_class = None

    def get_queryset(self):
        return Category.objects.filter(is_active=True).order_by(Lower('name'))

    def list(self, request, *args, **kwargs):
        """нормализуем параметры для ключа кэша"""
        params = {
            "search": (request.query_params.get("search") or "").strip().lower(),
        }
        cache_key = f"categories:list:{_hash_params(params)}"

        cached = cache.get(cache_key)
        if cached is not None:
            resp = Response(cached)
            resp["X-Cache"] = "HIT"
            return resp

        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        data = serializer.data

        cache.set(cache_key, data, timeout=_ttl_with_jitter(300, 0.10))
        resp = Response(data)
        resp["X-Cache"] = "MISS"
        return resp


class CategoryDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/categories/{id}/
    - Публичный детальник: 404 для неактивных категорий.
    - Ручной кэш по ключу category:{id}.
    - Заголовок X-Cache: HIT|MISS.
    """
    serializer_class = CategoryListSerializer
    throttle_classes = [AnonCatalogThrottle, UserCatalogThrottle]
    lookup_field = 'pk'

    def retrieve(self, request, *args, **kwargs):
        pk = kwargs.get("pk")
        cache_key = f"category:{pk}"

        cached = cache.get(cache_key)
        if cached is not None:
            resp = Response(cached)
            resp["X-Cache"] = "HIT"
            return resp

        # Публичный контракт: неактивные категории не выдаём
        instance = get_object_or_404(Category, pk=pk, is_active=True)

        serializer = self.get_serializer(instance)
        data = serializer.data
        cache.set(cache_key, data, timeout=_ttl_with_jitter(300, 0.10))

        resp = Response(data)
        resp["X-Cache"] = "MISS"
        return resp


class CategoryDeleteView(APIView):
    """
    - По умолчанию: мягкое удаление (is_active=False).
    - Жёсткое удаление: только админ и только с флагом ?hard=true, если нет связанных продуктов.
    Ответы:
    - 204 No Content — успешное soft/hard удаление.
    - 400 Bad Request — есть связанные продукты (code=category_in_use).
    - 403 Forbidden — нет прав (обеспечивает IsAdminUser).
    - 404 Not Found — категория не найдена.
    """
    permission_classes = [permissions.IsAdminUser]

    def delete(self, request, pk, *args, **kwargs):
        category = get_object_or_404(Category, pk=pk)
        hard = str(request.query_params.get("hard", "false")).lower() in ("1", "true", "yes")

        if hard:
            if category.products.exists():
                return Response(
                    {"detail": "Категория содержит продукты, удаление невозможно", "code": "category_in_use"},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            category.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

        category.soft_delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ProductListView(generics.ListAPIView):
    """
    Возвращает список активных продуктов.
    Фильтры:
    - is_active=true (по умолчанию)
    - search по name (подстрока, регистр нечувствителен)
    - фильтр по category_id
    Сортировка:
    - name ASC (по возрастанию)
    Пагинация:
    - отключена по умолчанию
    - если количество продуктов > 200 — включить page/size
    Кэширование:
    - TTL 5 минут
    Ответ:
    - 200 OK: массив объектов [{id, name, price, category_id}, ...]
    """
    queryset = Product.objects.filter(is_active=True).order_by(Lower('name'))
    serializer_class = ProductListSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']
    filterset_fields = ['category', 'price']
    pagination_class = None
