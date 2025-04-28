from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.views.generic import ListView, DetailView
from django.db.models import Q
from .models import Book, Author, Genre
from .services.openlibrary import OpenLibraryAPI
from .forms import BookSearchForm, ImportBookForm, UserBookForm
from rest_framework.decorators import api_view
from rest_framework.response import Response
from .serializers import BookSerializer, AuthorSerializer

class BookListView(ListView):
    model = Book
    context_object_name = 'books'
    template_name = 'books/book_list.html'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = Book.objects.all().prefetch_related('authors', 'genres')
        
        # Filter by search query if provided
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(title__icontains=query) | 
                Q(authors__name__icontains=query) |
                Q(description__icontains=query)
            ).distinct()
        
        # Filter by genre if provided
        genre = self.request.GET.get('genre')
        if genre:
            queryset = queryset.filter(genres__slug=genre)
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_form'] = BookSearchForm(self.request.GET or None)
        context['genres'] = Genre.objects.all()
        return context

class BookDetailView(DetailView):
    model = Book
    context_object_name = 'book'
    template_name = 'books/book_detail.html'
    slug_url_kwarg = 'slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.user.is_authenticated:
            try:
                user_book = self.object.user_books.get(user=self.request.user)
                context['user_book'] = user_book
                context['user_book_form'] = UserBookForm(instance=user_book)
            except self.object.user_books.model.DoesNotExist:
                context['user_book_form'] = UserBookForm()
        return context

class AuthorListView(ListView):
    model = Author
    context_object_name = 'authors'
    template_name = 'books/author_list.html'
    paginate_by = 50

class AuthorDetailView(DetailView):
    model = Author
    context_object_name = 'author'
    template_name = 'books/author_detail.html'
    slug_url_kwarg = 'slug'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['books'] = self.object.books.all()
        return context

@login_required
def search_openlibrary(request):
    results = []
    if request.method == 'POST':
        form = BookSearchForm(request.POST)
        if form.is_valid():
            query = form.cleaned_data['query']
            results = OpenLibraryAPI.search_books(query)
    else:
        form = BookSearchForm()
    
    return render(request, 'books/openlibrary_search.html', {
        'form': form,
        'results': results
    })

@login_required
def import_book(request):
    if request.method == 'POST':
        form = ImportBookForm(request.POST)
        if form.is_valid():
            isbn = form.cleaned_data.get('isbn')
            ol_work_key = form.cleaned_data.get('ol_work_key')
            
            book = OpenLibraryAPI.import_book_to_database(isbn=isbn, ol_work_key=ol_work_key)
            
            if book:
                return redirect('book_detail', slug=book.slug)
            else:
                form.add_error(None, "Could not import book. Please check the details and try again.")
    else:
        # Pre-populate from query parameters if available
        initial = {}
        if request.GET.get('isbn'):
            initial['isbn'] = request.GET.get('isbn')
        if request.GET.get('ol_work_key'):
            initial['ol_work_key'] = request.GET.get('ol_work_key')
            
        form = ImportBookForm(initial=initial)
    
    return render(request, 'books/import_book.html', {'form': form})

@login_required
def update_user_book(request, book_slug):
    book = get_object_or_404(Book, slug=book_slug)
    
    if request.method == 'POST':
        try:
            user_book = book.user_books.get(user=request.user)
            form = UserBookForm(request.POST, instance=user_book)
        except book.user_books.model.DoesNotExist:
            form = UserBookForm(request.POST)
        
        if form.is_valid():
            user_book = form.save(commit=False)
            user_book.book = book
            user_book.user = request.user
            user_book.save()
            return redirect('book_detail', slug=book.slug)
    
    return redirect('book_detail', slug=book.slug)

@api_view(['GET', 'POST'])
def api_book_list(request):
    """API endpoint for listing and creating books"""
    if request.method == 'GET':
        books = Book.objects.all().prefetch_related('authors', 'genres')
        
        # Handle search query
        query = request.query_params.get('q')
        if query:
            books = books.filter(
                Q(title__icontains=query) | 
                Q(authors__name__icontains=query) |
                Q(description__icontains=query)
            ).distinct()
        
        # Handle genre filter
        genre = request.query_params.get('genre')
        if genre:
            books = books.filter(genres__slug=genre)
        
        serializer = BookSerializer(books, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = BookSerializer(data=request.data)
        if serializer.is_valid():
            # Save the book
            book = serializer.save()
            
            # Handle authors
            if 'authors' in request.data:
                author_ids = [author.get('id') for author in request.data['authors']]
                book.authors.set(Author.objects.filter(id__in=author_ids))
            
            # Handle genres
            if 'genres' in request.data:
                genre_ids = [genre.get('id') for genre in request.data['genres']]
                book.genres.set(Genre.objects.filter(id__in=genre_ids))
            
            return Response(BookSerializer(book).data, status=201)
        return Response(serializer.errors, status=400)

@api_view(['GET', 'PUT', 'DELETE'])
def api_book_detail(request, slug):
    """API endpoint for retrieving, updating and deleting a book"""
    try:
        book = Book.objects.get(slug=slug)
    except Book.DoesNotExist:
        return Response({"error": "Book not found"}, status=404)
    
    if request.method == 'GET':
        serializer = BookSerializer(book)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = BookSerializer(book, data=request.data, partial=True)
        if serializer.is_valid():
            # Save the book
            book = serializer.save()
            
            # Handle authors
            if 'authors' in request.data:
                author_ids = [author.get('id') for author in request.data['authors']]
                book.authors.set(Author.objects.filter(id__in=author_ids))
            
            # Handle genres
            if 'genres' in request.data:
                genre_ids = [genre.get('id') for genre in request.data['genres']]
                book.genres.set(Genre.objects.filter(id__in=genre_ids))
            
            return Response(BookSerializer(book).data)
        return Response(serializer.errors, status=400)
    
    elif request.method == 'DELETE':
        book.delete()
        return Response(status=204)

@api_view(['GET', 'POST'])
def api_author_list(request):
    """API endpoint for listing and creating authors"""
    if request.method == 'GET':
        authors = Author.objects.all()
        
        # Handle search query
        query = request.query_params.get('q')
        if query:
            authors = authors.filter(name__icontains=query)
        
        serializer = AuthorSerializer(authors, many=True)
        return Response(serializer.data)
    
    elif request.method == 'POST':
        serializer = AuthorSerializer(data=request.data)
        if serializer.is_valid():
            author = serializer.save()
            return Response(AuthorSerializer(author).data, status=201)
        return Response(serializer.errors, status=400)

@api_view(['GET', 'PUT', 'DELETE'])
def api_author_detail(request, slug):
    """API endpoint for retrieving, updating and deleting an author"""
    try:
        author = Author.objects.get(slug=slug)
    except Author.DoesNotExist:
        return Response({"error": "Author not found"}, status=404)
    
    if request.method == 'GET':
        serializer = AuthorSerializer(author)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        serializer = AuthorSerializer(author, data=request.data, partial=True)
        if serializer.is_valid():
            author = serializer.save()
            return Response(AuthorSerializer(author).data)
        return Response(serializer.errors, status=400)
    
    elif request.method == 'DELETE':
        author.delete()
        return Response(status=204)
