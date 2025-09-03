from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.catalog.models import Category


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
