from django.urls import path
from . import views

app_name = 'books'

urlpatterns = [
    # Web views (non-API)
    path('', views.BookListView.as_view(), name='book_list'),
    path('book/<slug:slug>/', views.BookDetailView.as_view(), name='book_detail'),
    path('book/<slug:book_slug>/update/', views.update_user_book, name='update_user_book'),
    path('authors/', views.AuthorListView.as_view(), name='author_list'),
    path('author/<slug:slug>/', views.AuthorDetailView.as_view(), name='author_detail'),
    path('search/', views.search_openlibrary, name='search_openlibrary'),
    path('import/', views.import_book, name='import_book'),

    # API endpoints - renamed to follow the /api/books pattern
    path('api/books/', views.api_book_list, name='api_book_list'),
    path('api/books/<slug:slug>/', views.api_book_detail, name='api_book_detail'),
    path('api/authors/', views.api_author_list, name='api_author_list'),
    path('api/authors/<slug:slug>/', views.api_author_detail, name='api_author_detail'),
]
