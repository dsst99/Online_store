from django.db.models.functions import Lower
from django.shortcuts import get_object_or_404
from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import filters
from apps.catalog.models import Category, Product
from apps.catalog.serializers import CategoryListSerializer, ProductListSerializer
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page


@method_decorator(cache_page(60 * 5), name='dispatch')
class CategoryListView(generics.ListAPIView):
    """
    Возвращает список активных категорий.
    Фильтры:
    - is_active=true (по умолчанию)
    - search по name (подстрока, регистр нечувствителен)
    Сортировка:
    - name ASC (по возрастанию)
    Пагинация:
    - отключена по умолчанию
    - если количество категорий > 200 — можно включить page/size
    Кэширование:
    - ключ: categories:list
    - TTL: 5 минут (+/- 10% джиттер)
    Заголовки:
    - ETag / Last-Modified (опционально)
    - X-Cache: HIT | MISS
    Ответ:
    - 200 OK: массив объектов [{id, name, slug}, ...]
    """
    queryset = Category.objects.filter(is_active=True).order_by(Lower('name'))
    serializer_class = CategoryListSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']
    pagination_class = None


@method_decorator(cache_page(60 * 5, key_prefix="category"), name='dispatch')
class CategoryDetailView(generics.RetrieveAPIView):
    """
    Возвращает детали категории:
    - id, name, slug, is_active, created_at, updated_at
    Кэш:
    - ключ: category:{id}, TTL 5 минут
    """
    queryset = Category.objects.all()
    serializer_class = CategoryListSerializer


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
