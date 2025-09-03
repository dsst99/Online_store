from django.urls import path
from .views import (
    CategoryListView,
    CategoryDeleteView,
    ProductListView,
)

urlpatterns = [
    # Категории
    path('api/v1/categories/', CategoryListView.as_view(), name="category_list"),
    path('api/categories/<int:pk>/', CategoryDeleteView.as_view(), name="category_delete"),

    # Продукты
    path('api/v1/products/', ProductListView.as_view(), name="product_list"),
]
