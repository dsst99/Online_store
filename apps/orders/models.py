from django.db import models
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


class Product(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    stock = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class Order(models.Model):
    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_SHIPPED = 'shipped'
    STATUS_DELIVERED = 'delivered'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = [
        (STATUS_PENDING, 'Pending'),
        (STATUS_PROCESSING, 'Processing'),
        (STATUS_SHIPPED, 'Shipped'),
        (STATUS_DELIVERED, 'Delivered'),
        (STATUS_CANCELLED, 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name='orders')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    products = models.ManyToManyField(Product, through='OrderItem', related_name='orders')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def clean(self):
        """Валидируем переход статуса"""
        valid_transitions = {
            self.STATUS_PENDING: [self.STATUS_PROCESSING, self.STATUS_CANCELLED],
            self.STATUS_PROCESSING: [self.STATUS_SHIPPED, self.STATUS_CANCELLED],
            self.STATUS_SHIPPED: [self.STATUS_DELIVERED],
            self.STATUS_DELIVERED: [],
            self.STATUS_CANCELLED: [],
        }

        if self.pk:  # Только для уже существующих объектов
            old_status = Order.objects.get(pk=self.pk).status
            if self.status != old_status:
                if self.status not in valid_transitions[old_status]:
                    raise ValidationError(f"Невозможно изменить статус {old_status} → {self.status}")

        if self.total_price < 0:
            raise ValidationError("total_price не может быть меньше 0")

    def save(self, *args, **kwargs):
        """Пересчёт total_price перед сохранением"""
        self.total_price = sum(
            item.quantity * item.price for item in self.items.all()
        )
        super().save(*args, **kwargs)

    @property
    def is_readonly(self):
        return self.status in [self.STATUS_SHIPPED, self.STATUS_DELIVERED, self.STATUS_CANCELLED]


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=8, decimal_places=2)

    class Meta:
        unique_together = ('order', 'product')

    def clean(self):
        """Запрет изменений состава, если статус финальный"""
        if self.order.is_readonly:
            raise ValidationError("Нельзя изменять состав заказа после отправки/доставки/отмены")

    def save(self, *args, **kwargs):
        if not self.price:
            self.price = self.product.price
        super().save(*args, **kwargs)
