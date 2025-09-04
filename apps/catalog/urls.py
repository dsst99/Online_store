from django.urls import path
from .views import (
    CategoryListView,
    CategoryDeleteView,
    CategoryDetailView,
    ProductListView, ProductDetailView,
)

urlpatterns = [
    # Категории
    path('api/v1/categories/', CategoryListView.as_view(), name="category_list"),
    path('api/v1/categories/<int:pk>/', CategoryDetailView.as_view(), name="category_detail"),
    path('api/v1/categories/<int:pk>/delete/', CategoryDeleteView.as_view(), name="category_delete"),

    # Продукты
    path('api/v1/products/', ProductListView.as_view(), name="product_list"),
    path('api/v1/products/<int:pk>/', ProductDetailView.as_view(), name="product_detail"),
]
