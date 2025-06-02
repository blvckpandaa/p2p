from rest_framework import serializers
from django.utils import timezone
from p2p.models import Order, Transaction, Message
from users.api.serializers import UserSerializer

class OrderSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    is_expired = serializers.BooleanField(read_only=True)
    total_price = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    expires_in = serializers.SerializerMethodField()
    
    class Meta:
        model = Order
        fields = (
            'id', 'user', 'type', 'token_type', 'amount', 'price_per_unit',
            'min_amount', 'payment_details', 'status', 'created_at',
            'expires_at', 'is_expired', 'total_price', 'expires_in'
        )
        read_only_fields = ('id', 'user', 'created_at', 'is_expired', 'total_price')
    
    def get_expires_in(self, obj):
        """Вычисляет время до истечения срока действия ордера в секундах"""
        if obj.expires_at and obj.expires_at > timezone.now():
            return int((obj.expires_at - timezone.now()).total_seconds())
        return 0
    
    def validate(self, data):
        """Проверка данных перед созданием или обновлением ордера"""
        # Если это обновление, проверяем статус
        if self.instance and self.instance.status in ['completed', 'cancelled']:
            raise serializers.ValidationError("Нельзя редактировать завершенный или отмененный ордер")
        
        # Проверка минимальной суммы
        if data.get('min_amount') and data.get('amount'):
            if data['min_amount'] > data['amount']:
                raise serializers.ValidationError(
                    "Минимальная сумма не может быть больше общей суммы ордера"
                )
        
        return data


class OrderCreateSerializer(serializers.ModelSerializer):
    """Сериализатор для создания ордера"""
    class Meta:
        model = Order
        fields = (
            'type', 'token_type', 'amount', 'price_per_unit',
            'min_amount', 'payment_details'
        )
    
    def validate(self, data):
        """Проверка данных перед созданием ордера"""
        user = self.context['request'].user
        
        # Проверка доступа к P2P-бирже
        if not user.has_p2p_access:
            raise serializers.ValidationError("У вас нет доступа к P2P-бирже")
        
        # Проверка баланса пользователя для ордера на продажу
        if data['type'] == 'sell':
            token_type = data['token_type']
            amount = data['amount']
            
            if token_type == 'CF' and user.cf_balance < amount:
                raise serializers.ValidationError(
                    f"Недостаточно средств на балансе. Требуется {amount} CF, доступно {user.cf_balance} CF"
                )
            elif token_type == 'TON' and user.ton_balance < amount:
                raise serializers.ValidationError(
                    f"Недостаточно средств на балансе. Требуется {amount} TON, доступно {user.ton_balance} TON"
                )
            elif token_type == 'NOT' and user.not_balance < amount:
                raise serializers.ValidationError(
                    f"Недостаточно средств на балансе. Требуется {amount} NOT, доступно {user.not_balance} NOT"
                )
        
        # Проверка минимальной суммы
        if data['min_amount'] > data['amount']:
            raise serializers.ValidationError(
                "Минимальная сумма не может быть больше общей суммы ордера"
            )
        
        return data
    
    def create(self, validated_data):
        """Создание нового ордера"""
        user = self.context['request'].user
        
        # Создаем ордер
        order = Order.objects.create(
            user=user,
            **validated_data,
            expires_at=timezone.now() + timezone.timedelta(days=3)  # Срок действия ордера по умолчанию
        )
        
        # Если это ордер на продажу, блокируем средства на балансе пользователя
        if order.type == 'sell':
            if order.token_type == 'CF':
                user.cf_balance -= order.amount
            elif order.token_type == 'TON':
                user.ton_balance -= order.amount
            elif order.token_type == 'NOT':
                user.not_balance -= order.amount
            
            user.save()
        
        return order


class TransactionSerializer(serializers.ModelSerializer):
    order = OrderSerializer(read_only=True)
    buyer = UserSerializer(read_only=True)
    seller = UserSerializer(read_only=True)
    total_price = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    total_with_commission = serializers.DecimalField(max_digits=15, decimal_places=2, read_only=True)
    
    class Meta:
        model = Transaction
        fields = (
            'id', 'order', 'buyer', 'seller', 'amount', 'price_per_unit',
            'token_type', 'commission', 'status', 'created_at', 'updated_at',
            'total_price', 'total_with_commission'
        )
        read_only_fields = (
            'id', 'order', 'buyer', 'seller', 'amount', 'price_per_unit',
            'token_type', 'commission', 'created_at', 'updated_at',
            'total_price', 'total_with_commission'
        )


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSerializer(read_only=True)
    recipient = UserSerializer(read_only=True, source='recipient')
    
    class Meta:
        model = Message
        fields = (
            'id', 'transaction', 'sender', 'recipient', 'content',
            'is_read', 'created_at'
        )
        read_only_fields = ('id', 'transaction', 'sender', 'is_read', 'created_at')
    
    def create(self, validated_data):
        user = self.context['request'].user
        transaction = validated_data['transaction']
        
        # Проверка, что пользователь является участником транзакции
        if user != transaction.buyer and user != transaction.seller:
            raise serializers.ValidationError("Вы не являетесь участником этой сделки")
        
        # Создаем сообщение
        message = Message.objects.create(
            transaction=transaction,
            sender=user,
            content=validated_data['content']
        )
        
        return message 