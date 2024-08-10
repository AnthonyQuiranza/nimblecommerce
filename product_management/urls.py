from django.urls import path
from . import views

urlpatterns = [
    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.add_product, name='add_product'),
    path('products/edit/', views.edit_product, name='edit_product'),
    path('products/<int:product_id>/', views.get_product_details, name='get_product_details'),
    path('upload-image/', views.upload_image, name='upload_image'),
]