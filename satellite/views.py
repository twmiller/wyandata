from django.shortcuts import render
from rest_framework import viewsets, permissions, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import EMWINFile
from .serializers import EMWINFileSerializer

class EMWINFileViewSet(viewsets.ModelViewSet):
    """ViewSet for EMWIN file API"""
    queryset = EMWINFile.objects.all().order_by('-source_datetime')
    serializer_class = EMWINFileSerializer
    # Remove authentication requirement for internal API
    permission_classes = [permissions.AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['product_id', 'station_id', 'wmo_header', 'parsed', 'has_been_read',
                       'station_country', 'station_state']
    search_fields = ['filename', 'product_id', 'product_name', 'station_id', 'station_name', 
                     'preview', 'station_location']
    ordering_fields = ['source_datetime', 'last_modified', 'filename', 'size_bytes']
    
    @action(detail=False, methods=['get'])
    def categories(self, request):
        """Return unique product categories"""
        categories = EMWINFile.objects.values_list('product_category', flat=True).distinct()
        return Response(sorted(filter(None, categories)))
    
    @action(detail=False, methods=['get'])
    def stations(self, request):
        """Return unique stations with counts"""
        stations = EMWINFile.objects.values('station_id', 'station_name').distinct()
        station_counts = {}
        
        for station in stations:
            if station['station_id']:
                count = EMWINFile.objects.filter(station_id=station['station_id']).count()
                station_counts[station['station_id']] = {
                    'id': station['station_id'],
                    'name': station['station_name'],
                    'count': count
                }
                
        return Response(list(station_counts.values()))
    
    @action(detail=False, methods=['get'])
    def products(self, request):
        """Return unique product IDs with counts and names"""
        products = EMWINFile.objects.values('product_id', 'product_name', 'product_category').distinct()
        product_counts = {}
        
        for product in products:
            if product['product_id']:
                count = EMWINFile.objects.filter(product_id=product['product_id']).count()
                product_counts[product['product_id']] = {
                    'id': product['product_id'],
                    'name': product['product_name'],
                    'category': product['product_category'],
                    'count': count
                }
                
        return Response(list(product_counts.values()))
    
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
