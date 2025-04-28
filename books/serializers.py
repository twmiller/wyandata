from rest_framework import serializers
from .models import Book, Author, Genre, Publisher

class GenreSerializer(serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ['id', 'name', 'slug', 'description']
        read_only_fields = ['id']

class PublisherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Publisher
        fields = ['id', 'name', 'website']
        read_only_fields = ['id']

class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Author
        fields = ['id', 'name', 'slug', 'biography', 'birth_date', 'death_date', 'ol_author_key']
        read_only_fields = ['id', 'slug']
        
class BookSerializer(serializers.ModelSerializer):
    authors = AuthorSerializer(many=True, read_only=True)
    genres = GenreSerializer(many=True, read_only=True)
    publisher = PublisherSerializer(read_only=True)
    publisher_id = serializers.UUIDField(write_only=True, required=False)
    
    class Meta:
        model = Book
        fields = [
            'id', 'title', 'slug', 'authors', 'genres', 'publisher', 'publisher_id',
            'publication_date', 'isbn_10', 'isbn_13', 'description',
            'cover_image', 'page_count', 'ol_work_key', 'ol_edition_key',
            'language', 'added_date', 'updated_date'
        ]
        read_only_fields = ['id', 'slug', 'added_date', 'updated_date']
    
    def create(self, validated_data):
        publisher_id = validated_data.pop('publisher_id', None)
        
        # Create the book instance
        book = Book.objects.create(**validated_data)
        
        # Set the publisher if provided
        if publisher_id:
            try:
                publisher = Publisher.objects.get(id=publisher_id)
                book.publisher = publisher
                book.save()
            except Publisher.DoesNotExist:
                pass
                
        return book
    
    def update(self, instance, validated_data):
        publisher_id = validated_data.pop('publisher_id', None)
        
        # Update the book fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Update publisher if provided
        if publisher_id:
            try:
                publisher = Publisher.objects.get(id=publisher_id)
                instance.publisher = publisher
            except Publisher.DoesNotExist:
                pass
                
        instance.save()
        return instance
