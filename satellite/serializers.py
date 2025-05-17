from rest_framework import serializers
from .models import EMWINFile

class EMWINFileSerializer(serializers.ModelSerializer):
    """Serializer for EMWIN File model"""
    age_in_hours = serializers.FloatField(read_only=True)
    file_extension = serializers.CharField(read_only=True)
    has_coordinates = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = EMWINFile
        fields = '__all__'
        read_only_fields = ('created_at', 'updated_at')
