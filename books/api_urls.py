from django.urls import path
from . import views

app_name = 'books_api'

urlpatterns = [
    # API endpoints at /api/books/... to match pattern of other apps
    path('books/', views.api_book_list, name='api_book_list'),
    path('books/<slug:slug>/', views.api_book_detail, name='api_book_detail'),
    path('authors/', views.api_author_list, name='api_author_list'),
    path('authors/<slug:slug>/', views.api_author_detail, name='api_author_detail'),
]
