from django.contrib import admin
from .models import Book, Author, Genre, Publisher, UserBook

@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('name', 'birth_date', 'death_date')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Genre)
class GenreAdmin(admin.ModelAdmin):
    list_display = ('name',)
    prepopulated_fields = {'slug': ('name',)}

@admin.register(Publisher)
class PublisherAdmin(admin.ModelAdmin):
    list_display = ('name', 'website')
    search_fields = ('name',)

class AuthorInline(admin.TabularInline):
    model = Book.authors.through
    extra = 1

class GenreInline(admin.TabularInline):
    model = Book.genres.through
    extra = 1

@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ('title', 'display_authors', 'publication_date', 'display_genres')
    list_filter = ('publication_date', 'genres')
    search_fields = ('title', 'authors__name', 'description')
    prepopulated_fields = {'slug': ('title',)}
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'description', 'publisher', 'publication_date', 'language')
        }),
        ('Identification', {
            'fields': ('isbn_10', 'isbn_13', 'cover_image', 'page_count')
        }),
        ('OpenLibrary', {
            'fields': ('ol_work_key', 'ol_edition_key'),
            'classes': ('collapse',)
        }),
    )
    inlines = [AuthorInline, GenreInline]
    
    def display_authors(self, obj):
        return ", ".join([author.name for author in obj.authors.all()])
    display_authors.short_description = 'Authors'
    
    def display_genres(self, obj):
        return ", ".join([genre.name for genre in obj.genres.all()])
    display_genres.short_description = 'Genres'

@admin.register(UserBook)
class UserBookAdmin(admin.ModelAdmin):
    list_display = ('user', 'book', 'status', 'rating', 'acquired_date', 'read_date')
    list_filter = ('status', 'rating', 'user')
    search_fields = ('book__title', 'review')
