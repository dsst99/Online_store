from django.urls import path
from .views import (
    CategoryListView,
    CategoryDeleteView,
    CategoryDetailView,
    ProductListView, ProductDetailView,
)

urlpatterns = [
    # Категории
    path('categories/', CategoryListView.as_view(), name="category_list"),
    path('categories/<int:pk>/', CategoryDetailView.as_view(), name="category_detail"),
    path('categories/<int:pk>/delete/', CategoryDeleteView.as_view(), name="category_delete"),

    # Продукты
    path('products/', ProductListView.as_view(), name="product_list"),
    path('products/<int:pk>/', ProductDetailView.as_view(), name="product_detail"),
]
