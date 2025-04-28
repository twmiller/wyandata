from django.db import models
import uuid
from django.utils.text import slugify

class Author(models.Model):
    """Represents a book author"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    biography = models.TextField(blank=True)
    birth_date = models.DateField(null=True, blank=True)
    death_date = models.DateField(null=True, blank=True)
    ol_author_key = models.CharField(max_length=100, blank=True, help_text="OpenLibrary author key")
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']

class Genre(models.Model):
    """Represents book genres/categories"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']

class Publisher(models.Model):
    """Represents a book publisher"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    website = models.URLField(blank=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        ordering = ['name']

class Book(models.Model):
    """Represents a book in the library"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True, blank=True)
    authors = models.ManyToManyField(Author, related_name='books')
    genres = models.ManyToManyField(Genre, related_name='books', blank=True)
    publisher = models.ForeignKey(Publisher, on_delete=models.SET_NULL, null=True, blank=True, related_name='books')
    
    # Dates
    publication_date = models.DateField(null=True, blank=True, help_text="Original publication date")
    isbn_10 = models.CharField(max_length=10, blank=True, help_text="10-digit ISBN")
    isbn_13 = models.CharField(max_length=13, blank=True, help_text="13-digit ISBN")
    
    # Content
    description = models.TextField(blank=True)
    cover_image = models.ImageField(upload_to='book_covers/', null=True, blank=True)
    page_count = models.PositiveIntegerField(null=True, blank=True)
    
    # OpenLibrary integration fields
    ol_work_key = models.CharField(max_length=100, blank=True, help_text="OpenLibrary work key")
    ol_edition_key = models.CharField(max_length=100, blank=True, help_text="OpenLibrary edition key")
    
    # Book meta
    language = models.CharField(max_length=50, blank=True)
    added_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return self.title
    
    class Meta:
        ordering = ['title']

class UserBook(models.Model):
    """Represents a user's relationship with a book (e.g., owned, read, wishlist)"""
    STATUS_CHOICES = (
        ('owned', 'Owned'),
        ('read', 'Read'),
        ('reading', 'Currently Reading'),
        ('to_read', 'Want to Read'),
        ('wishlist', 'Wishlist'),
    )
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='user_books')
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='user_books')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='owned')
    rating = models.PositiveSmallIntegerField(null=True, blank=True, help_text="Rating from 1-5")
    review = models.TextField(blank=True)
    acquired_date = models.DateField(null=True, blank=True)
    read_date = models.DateField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.book.title} ({self.get_status_display()})"
    
    class Meta:
        unique_together = ('book', 'user')
