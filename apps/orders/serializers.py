from collections import defaultdict

from django.db import transaction
from django.db.models import F
from rest_framework import serializers

from apps.catalog.models import Product
from apps.orders.models import Order, OrderItem


# ---------- ВСПОМОГАТЕЛЬНЫЕ ----------

class OrderItemInputSerializer(serializers.Serializer):
    """Входная позиция при создании заказа."""
    product_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1)

    def validate(self, attrs):
        # базовая нормализация
        return attrs


class OrderItemReadSerializer(serializers.ModelSerializer):
    """Позиция заказа (для чтения)."""
    product_name = serializers.CharField(source="product.name", read_only=True)

    class Meta:
        model = OrderItem
        fields = ("id", "product", "product_name", "quantity", "price_at_purchase", "created_at")
        read_only_fields = fields


# ---------- СОЗДАНИЕ ЗАКАЗА ----------

class OrderCreateSerializer(serializers.Serializer):
    """
    Создание заказа:
      - принимает список позиций [{product_id, quantity}, ...]
      - агрегирует дубликаты product_id
      - в транзакции: select_for_update по продуктам, проверка stock, списание, создание Order + OrderItem[]
      - пересчитывает total_price через order.recalc_total()
    """
    items = OrderItemInputSerializer(many=True)

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError("Список позиций пуст.")
        # агрегируем количество по одному продукту
        aggregated = defaultdict(int)
        for it in items:
            aggregated[it["product_id"]] += it["quantity"]
        # превращаем обратно в нормализованный список
        normalized = [{"product_id": pid, "quantity": qty} for pid, qty in aggregated.items()]
        return normalized

    def create(self, validated_data):
        user = self.context["request"].user
        items = validated_data["items"]

        product_ids = [i["product_id"] for i in items]

        with transaction.atomic():
            # блокируем продукты для исключения гонок
            products_qs = (
                Product.objects
                .select_for_update()
                .filter(pk__in=product_ids, is_active=True)
            )
            products_by_id = {p.id: p for p in products_qs}

            # проверяем, что все продукты существуют и активны
            missing = set(product_ids) - set(products_by_id.keys())
            if missing:
                raise serializers.ValidationError(
                    {"items": [f"Продукт(ы) не найдены или неактивны: {sorted(missing)}"]}
                )

            # проверка stock
            errors = []
            for it in items:
                prod = products_by_id[it["product_id"]]
                requested = it["quantity"]
                if prod.stock < requested:
                    errors.append(
                        {"product_id": prod.id, "available": prod.stock, "requested": requested}
                    )
            if errors:
                raise serializers.ValidationError(
                    {"stock": "Недостаточно товара на складе", "details": errors}
                )

            # создаём заказ
            order = Order.objects.create(user=user, status=Order.STATUS_PENDING)

            # списываем stock и создаём позиции
            order_items = []
            for it in items:
                prod = products_by_id[it["product_id"]]
                qty = it["quantity"]

                # списание
                Product.objects.filter(pk=prod.pk).update(stock=F("stock") - qty)
                prod.stock -= qty  # локально тоже уменьшим, чтобы price_at_purchase брался с актуального объекта

                order_items.append(
                    OrderItem(order=order, product=prod, quantity=qty, price_at_purchase=prod.price)
                )
            OrderItem.objects.bulk_create(order_items)

            # пересчёт total
            order.recalc_total(save=True)

        return order


# ---------- ЧТЕНИЕ ЗАКАЗОВ ----------

class OrderListSerializer(serializers.ModelSerializer):
    """Список заказов (кратко)."""
    items_count = serializers.IntegerField(source="items.count", read_only=True)

    class Meta:
        model = Order
        fields = ("id", "status", "total_price", "created_at", "updated_at", "items_count")
        read_only_fields = fields


class OrderDetailSerializer(serializers.ModelSerializer):
    """Детали заказа со списком позиций."""
    items = OrderItemReadSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = ("id", "user", "status", "total_price", "created_at", "updated_at", "items")
        read_only_fields = fields


# ---------- PATCH СТАТУСА ----------

class OrderStatusPatchSerializer(serializers.ModelSerializer):
    """
    Обновление статуса (PATCH).
    Переходы валидируются на уровне модели (clean()).
    """
    class Meta:
        model = Order
        fields = ("status",)

    def update(self, instance: Order, validated_data):
        new_status = validated_data["status"]
        # применяем и валидируем
        instance.status = new_status
        instance.full_clean()  # дергает Order.clean() с валидацией перехода
        instance.save(update_fields=["status", "updated_at"])
        return instance
