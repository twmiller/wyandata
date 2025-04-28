import requests
import logging
from datetime import datetime
from ..models import Book, Author, Publisher

logger = logging.getLogger(__name__)

class OpenLibraryAPI:
    """Service for interacting with OpenLibrary API"""
    BASE_URL = "https://openlibrary.org/api"
    SEARCH_URL = "https://openlibrary.org/search.json"
    
    @staticmethod
    def search_books(query, limit=10):
        """Search for books by title, author, ISBN, etc."""
        try:
            params = {
                'q': query,
                'limit': limit
            }
            response = requests.get(OpenLibraryAPI.SEARCH_URL, params=params)
            response.raise_for_status()
            data = response.json()
            
            results = []
            for doc in data.get('docs', []):
                result = {
                    'title': doc.get('title', 'Unknown Title'),
                    'authors': doc.get('author_name', []),
                    'year': doc.get('first_publish_year'),
                    'isbn': doc.get('isbn', []),
                    'ol_work_key': doc.get('key', '').replace('/works/', ''),
                    'cover_id': doc.get('cover_i'),
                    'language': doc.get('language', []),
                }
                results.append(result)
            
            return results
        except Exception as e:
            logger.error(f"Error searching OpenLibrary: {e}")
            return []
    
    @staticmethod
    def get_book_by_isbn(isbn):
        """Get book details by ISBN"""
        try:
            url = f"{OpenLibraryAPI.BASE_URL}/books"
            params = {'bibkeys': f"ISBN:{isbn}", 'format': 'json', 'jscmd': 'data'}
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            if f"ISBN:{isbn}" in data:
                return data[f"ISBN:{isbn}"]
            return None
        except Exception as e:
            logger.error(f"Error fetching book by ISBN from OpenLibrary: {e}")
            return None
    
    @staticmethod
    def get_book_details(ol_work_key):
        """Get detailed information about a book by OpenLibrary work key"""
        try:
            url = f"https://openlibrary.org/works/{ol_work_key}.json"
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error fetching book details from OpenLibrary: {e}")
            return None
    
    @staticmethod
    def import_book_to_database(isbn=None, ol_work_key=None):
        """
        Import a book from OpenLibrary to the database
        Provide either ISBN or OpenLibrary work key
        """
        book_data = None
        
        # First try by ISBN if provided
        if isbn:
            book_data = OpenLibraryAPI.get_book_by_isbn(isbn)
            
        # Then try by work key if provided or if ISBN search failed
        if not book_data and ol_work_key:
            book_data = OpenLibraryAPI.get_book_details(ol_work_key)
        
        if not book_data:
            return None
            
        # Create or update the book
        book, created = Book.objects.get_or_create(
            ol_work_key=book_data.get('key', '').replace('/works/', ''),
            defaults={
                'title': book_data.get('title', 'Unknown Title'),
                'description': book_data.get('description', {}).get('value', '') if isinstance(book_data.get('description'), dict) else book_data.get('description', ''),
                'isbn_10': book_data.get('identifiers', {}).get('isbn_10', [''])[0] if book_data.get('identifiers', {}).get('isbn_10') else '',
                'isbn_13': book_data.get('identifiers', {}).get('isbn_13', [''])[0] if book_data.get('identifiers', {}).get('isbn_13') else '',
                'language': book_data.get('language', {}).get('key', '').replace('/languages/', '') if isinstance(book_data.get('language'), dict) else '',
            }
        )
        
        # Handle publication date
        if 'publish_date' in book_data:
            try:
                # Try to parse the date, handling various formats
                pub_date = book_data.get('publish_date')
                if isinstance(pub_date, str):
                    # Try different formats
                    for fmt in ['%Y', '%Y-%m-%d', '%B %d, %Y', '%Y-%m']:
                        try:
                            book.publication_date = datetime.strptime(pub_date, fmt).date()
                            break
                        except ValueError:
                            continue
            except Exception as e:
                logger.warning(f"Could not parse publication date: {e}")
        
        # Handle authors
        if 'authors' in book_data and isinstance(book_data['authors'], list):
            for author_data in book_data['authors']:
                author_name = author_data.get('name', '')
                author_key = author_data.get('key', '').replace('/authors/', '')
                
                if author_name:
                    author, _ = Author.objects.get_or_create(
                        ol_author_key=author_key,
                        defaults={'name': author_name}
                    )
                    book.authors.add(author)
        
        # Handle publisher
        if 'publishers' in book_data and isinstance(book_data['publishers'], list) and book_data['publishers']:
            publisher_name = book_data['publishers'][0]
            publisher, _ = Publisher.objects.get_or_create(name=publisher_name)
            book.publisher = publisher
            
        # Save the updated book
        book.save()
        return book
