from rest_framework import serializers
from users.models import User

class UserSerializer(serializers.ModelSerializer):
    """Сериализатор для модели пользователя"""
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = ('telegram_id', 'username', 'first_name', 'last_name', 
                  'photo_url', 'full_name', 'referral_code')
        read_only_fields = fields
    
    def get_full_name(self, obj):
        """Возвращает полное имя пользователя"""
        return obj.get_full_name() 