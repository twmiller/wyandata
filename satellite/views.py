from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, permissions, filters, pagination
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Max, Min
from .models import EMWINFile, EMWINStation, EMWINProduct
from .serializers import EMWINFileSerializer, EMWINStationSerializer, EMWINProductSerializer
import os

class StandardResultsSetPagination(pagination.PageNumberPagination):
    """Standard pagination for all viewsets"""
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100

class EMWINFileViewSet(viewsets.ModelViewSet):
    """ViewSet for EMWIN file API"""
    queryset = EMWINFile.objects.all().order_by('-source_datetime')
    serializer_class = EMWINFileSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = {
        'product': ['exact'],
        'station': ['exact'],
        'wmo_header': ['exact'],
        'parsed': ['exact'],
        'has_been_read': ['exact'],
        'source_datetime': ['gte', 'lte', 'date', 'date__gte', 'date__lte'],
    }
    search_fields = ['filename', 'preview', 'product__name', 'product__product_id', 'station__name', 'station__station_id']
    ordering_fields = ['source_datetime', 'last_modified', 'filename', 'size_bytes']
    pagination_class = StandardResultsSetPagination

    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Return unique product categories"""
        categories = EMWINProduct.objects.values_list('category', flat=True).distinct()
        return Response(sorted(filter(None, categories)))
    
    @action(detail=True, methods=['get'])
    def content(self, request, pk=None):
        """Return the full content of an EMWIN file"""
        emwin_file = self.get_object()
        try:
            # Check if file exists
            if not os.path.exists(emwin_file.path):
                return Response({'error': 'File not found on disk'}, status=404)
                
            # Read the file content
            with open(emwin_file.path, 'r', errors='replace') as f:
                content = f.read()
            
            # Mark the file as read
            if not emwin_file.has_been_read:
                emwin_file.has_been_read = True
                emwin_file.save(update_fields=['has_been_read'])
            
            return Response({
                'id': emwin_file.id,
                'filename': emwin_file.filename,
                'content': content,
                'product_id': emwin_file.product_id,
                'product_name': emwin_file.product_name,
                'station_id': emwin_file.station_id,
                'station_name': emwin_file.station_name,
                'source_datetime': emwin_file.source_datetime,
            })
        except Exception as e:
            return Response({'error': f'Error reading file: {str(e)}'}, status=500)
    
    @action(detail=False, methods=['post'])
    def mark_read(self, request):
        """Mark files as read"""
        file_ids = request.data.get('ids', [])
        if not file_ids:
            return Response({'error': 'No file IDs provided'}, status=400)
            
        updated = EMWINFile.objects.filter(id__in=file_ids).update(has_been_read=True)
        return Response({'updated': updated})
    
    @action(detail=False, methods=['post'])
    def mark_unread(self, request):
        """Mark files as unread"""
        file_ids = request.data.get('ids', [])
        if not file_ids:
            return Response({'error': 'No file IDs provided'}, status=400)
            
        updated = EMWINFile.objects.filter(id__in=file_ids).update(has_been_read=False)
        return Response({'updated': updated})

class EMWINStationViewSet(viewsets.ModelViewSet):
    """ViewSet for EMWIN stations"""
    queryset = EMWINStation.objects.annotate(
        files_count=Count('emwinfiles')
    ).order_by('station_id')
    serializer_class = EMWINStationSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['country', 'state', 'type']
    search_fields = ['station_id', 'name', 'location']

class EMWINProductViewSet(viewsets.ModelViewSet):
    """ViewSet for EMWIN products"""
    queryset = EMWINProduct.objects.annotate(
        files_count=Count('emwinfiles')
    ).order_by('product_id')
    serializer_class = EMWINProductSerializer
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['category']
    search_fields = ['product_id', 'name', 'description']
