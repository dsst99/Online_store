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

    def __str__(self):
        return  self.id, self.name, self.slug, self.is_active, self.created_at, self.updated_at


class Product(models.Model):
    """
    Модель продукта.
    Поля:
    - category: категория продукта (ForeignKey на Category)
    - name: название продукта
    - price: цена
    - is_active: активность продукта (для soft delete)
    - created_at, updated_at: даты создания и обновления
    Правила:
    - Физическое удаление только через админку или при отсутствии связанных данных.
    - Soft delete: is_active=False
    """
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    name = models.CharField(max_length=250, verbose_name='название продукта')
    price = models.DecimalField(max_digits=8, decimal_places=2, verbose_name='цена')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    update_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name, self.price, self.is_active
