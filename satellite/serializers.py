from rest_framework import serializers
from .models import EMWINFile, EMWINStation, EMWINProduct

class EMWINStationSerializer(serializers.ModelSerializer):
    file_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = EMWINStation
        fields = '__all__'

class EMWINProductSerializer(serializers.ModelSerializer):
    file_count = serializers.IntegerField(read_only=True)
    
    class Meta:
        model = EMWINProduct
        fields = '__all__'

class EMWINFileSerializer(serializers.ModelSerializer):
    age_in_hours = serializers.FloatField(read_only=True)
    file_extension = serializers.CharField(read_only=True)
    has_coordinates = serializers.BooleanField(read_only=True)
    
    # Include nested data for product and station
    product_details = EMWINProductSerializer(source='product', read_only=True)
    station_details = EMWINStationSerializer(source='station', read_only=True)
    
    class Meta:
        model = EMWINFile
        fields = '__all__'
