from django.urls import path
from . import views

urlpatterns = [
    # API endpoints only - at the proper /api/books/ paths
    path('api/books/', views.api_book_list, name='api_book_list'),
    path('api/books/<slug:slug>/', views.api_book_detail, name='api_book_detail'),
    path('api/authors/', views.api_author_list, name='api_author_list'),
    path('api/authors/<slug:slug>/', views.api_author_detail, name='api_author_detail'),
]
