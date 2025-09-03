from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify


class Category(models.Model):
    """Модель для категорий товаров"""
    name = models.CharField(max_length=100, unique=True, help_text='Название категории')
    slug = models.SlugField(
        max_length=100,
        db_index=True,
        unique=True,
        verbose_name='Slug',
        help_text="Уникальный идентификатор категории в URL",
    )
    is_active = models.BooleanField(default=True, db_index=True, help_text='Активно')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, help_text='Обновлено')

    def save(self, *args, **kwargs):
        """
        Нормализация name/slug.
        - если slug пуст, генерируем из name; иначе нормализуем перед сохранением.
        - trim для name; защита от пустого slug после slugify.
        """
        if self.name:
            self.name = self.name.strip()

        base_slug = self.slug.strip() if self.slug else ""
        if not base_slug and self.name:
            base_slug = self.name

        self.slug = slugify(base_slug)[:100]
        if not self.slug:
            raise ValidationError('Slug не может быть пустым после нормализации')

        super().save(*args, **kwargs)

    def soft_delete(self):
        """мягкое удаление, (is_active = False)"""
        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'])

    class Meta:
        """Индекс для полей если понадобится выводить сортировкой товары по актуальности создания"""
        indexes = [
            models.Index(fields=['created_at']),
            models.Index(fields=['updated_at']),
        ]
        ordering = ['name']
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def __str__(self):
        return self.name


class Product(models.Model):
    """Модель для продуктов"""
    name = models.CharField(max_length=150, verbose_name='Название продукта')
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2, help_text='Цена')
    stock = models.PositiveIntegerField(default=0, verbose_name='На складе')
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        db_index=True,
        related_name='products',
        verbose_name='Категория',
    )
    is_active = models.BooleanField(default=True, db_index=True, verbose_name='Активно')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Создано')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Обновлено')

    def soft_delete(self):
        """мягкое удаление продукта (is_active = False)"""
        if self.is_active:
            self.is_active = False
            self.save(update_fields=['is_active', 'updated_at'])

    class Meta:
        """Проверка на отрицательную стоимость в БД и добавление индекса по цене B-Tree"""
        indexes = [
            models.Index(fields=['price']),
            models.Index(fields=['category', 'is_active', '-created_at']),
        ]
        constraints = [
            models.CheckConstraint(check=models.Q(price__gte=0), name='price__gte_0'),
            models.CheckConstraint(check=models.Q(stock__gte=0), name='stock__gte_0'),
        ]
        ordering = ['name']
        verbose_name = "Продукт"
        verbose_name_plural = 'Продукты'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.name:
            self.name = self.name.strip()
        super().save(*args, **kwargs)
