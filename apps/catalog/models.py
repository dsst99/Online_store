from django.db import models


class Category(models.Model):
    """Модель для категорий товаров"""
    name = models.CharField(max_length=100, verbose_name='Название продукта')
    slug = models.SlugField(max_length=100, db_index=True, unique=True)
    is_active = models.BooleanField(default=True, db_index=True, verbose_name='Активно')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')

    def soft_delete(self):
        """без удаления из бд, а просто как пометка неактивна"""
        self.is_active = False
        self.save()

    class Meta:
        """Индекс для полей если понадобится выводить сортировкой товары по актуальности создания"""
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at']),
        ]
