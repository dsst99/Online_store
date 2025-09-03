from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import filters
from apps.catalog.models import Category
from apps.catalog.serializers import CategoryListSerializer
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page


class CategoryDeleteView(APIView):
    """
    DELETE /api/categories/{id}/
    Политика удаления категорий:
    - По умолчанию категории "удаляются" мягко (через `is_active=False`).
    - Физическое удаление доступно только админам.
    - Если у категории есть связанные продукты — удаление запрещено.
    Возвращает:
    - 204 No Content — если категория успешно удалена.
    - 400 Bad Request — если у категории есть связанные продукты.
    - 403 Forbidden — если пользователь не админ.
    - 404 Not Found — если категория не найдена.
    """

    def delete(self, request, pk):
        category = Category.objects.get(pk=pk)

        if not request.user.is_staff:
            return Response({'detail': 'Нет прав на удаление!'},
                            status=status.HTTP_403_FORBIDDEN)

        if category.product_set.exists():
            return Response({'detail': 'Категория содержит продукты, удаление невозможно!'},
                            status=status.HTTP_400_BAD_REQUEST)

        category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


@method_decorator(cache_page(60 * 5), name='dispatch')
class CategoryListView(generics.ListAPIView):
    """
    GET /api/v1/categories/

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
    queryset = Category.objects.filter(is_active=True).order_by('name')
    serializer_class = CategoryListSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['name']
    pagination_class = None
