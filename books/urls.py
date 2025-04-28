from django.urls import path
from . import views

app_name = 'books'

urlpatterns = [
    # Book views
    path('', views.BookListView.as_view(), name='book_list'),
    path('book/<slug:slug>/', views.BookDetailView.as_view(), name='book_detail'),
    path('book/<slug:book_slug>/update/', views.update_user_book, name='update_user_book'),
    
    # Author views
    path('authors/', views.AuthorListView.as_view(), name='author_list'),
    path('author/<slug:slug>/', views.AuthorDetailView.as_view(), name='author_detail'),
    
    # OpenLibrary integration
    path('search/', views.search_openlibrary, name='search_openlibrary'),
    path('import/', views.import_book, name='import_book'),

    # API endpoints
    path('api/books/', views.api_book_list, name='api_book_list'),
    path('api/books/<slug:slug>/', views.api_book_detail, name='api_book_detail'),
    path('api/authors/', views.api_author_list, name='api_author_list'),
    path('api/authors/<slug:slug>/', views.api_author_detail, name='api_author_detail'),
]
