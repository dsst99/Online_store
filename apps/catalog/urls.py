from django.urls import path
from .views import (
    CategoryListView,
    CategoryView,
    ProductListView, ProductDetailView,
)

urlpatterns = [
    # Категории
    path('categories/', CategoryListView.as_view(), name="category-list"),
    path('categories/<int:pk>/', CategoryView.as_view(), name="category-detail"),

    # Продукты
    path('products/', ProductListView.as_view(), name="product-list"),
    path('products/<int:pk>/', ProductDetailView.as_view(), name="product-detail"),
]
