from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone
from django.conf import settings
from decimal import Decimal

from p2p.models import Order, Transaction, Message
from .serializers import (
    OrderSerializer, OrderCreateSerializer,
    TransactionSerializer, MessageSerializer
)
from p2p.permissions import HasP2PAccess, IsOrderOwner, IsTransactionParticipant


class OrderViewSet(viewsets.ModelViewSet):
    """
    API для работы с ордерами P2P-биржи
    """
    permission_classes = [permissions.IsAuthenticated, HasP2PAccess]
    serializer_class = OrderSerializer
    
    def get_queryset(self):
        """Возвращает ордера с фильтрацией"""
        # Базовый queryset с активными ордерами
        queryset = Order.objects.filter(status='active', expires_at__gt=timezone.now())
        
        # Фильтр по типу ордера (buy/sell)
        order_type = self.request.query_params.get('type')
        if order_type:
            queryset = queryset.filter(type=order_type)
        
        # Фильтр по типу токена
        token_type = self.request.query_params.get('token_type')
        if token_type:
            queryset = queryset.filter(token_type=token_type)
        
        # Фильтр по минимальной цене
        min_price = self.request.query_params.get('min_price')
        if min_price:
            queryset = queryset.filter(price_per_unit__gte=Decimal(min_price))
        
        # Фильтр по максимальной цене
        max_price = self.request.query_params.get('max_price')
        if max_price:
            queryset = queryset.filter(price_per_unit__lte=Decimal(max_price))
        
        # Исключаем ордера текущего пользователя
        exclude_own = self.request.query_params.get('exclude_own')
        if exclude_own and exclude_own.lower() == 'true':
            queryset = queryset.exclude(user=self.request.user)
        
        return queryset.select_related('user').order_by('-created_at')
    
    def get_serializer_class(self):
        """Выбор сериализатора в зависимости от действия"""
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer
    
    def perform_create(self, serializer):
        """Создание нового ордера"""
        serializer.save()
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, IsOrderOwner])
    def cancel(self, request, pk=None):
        """Отмена ордера"""
        order = self.get_object()
        
        if order.status != 'active':
            return Response(
                {"error": "Можно отменить только активный ордер"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Отменяем ордер
        order.status = 'cancelled'
        order.save()
        
        # Если это ордер на продажу, возвращаем средства на баланс
        if order.type == 'sell':
            user = order.user
            if order.token_type == 'CF':
                user.cf_balance += order.amount
            elif order.token_type == 'TON':
                user.ton_balance += order.amount
            elif order.token_type == 'NOT':
                user.not_balance += order.amount
            
            user.save()
        
        return Response(OrderSerializer(order).data)
    
    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def my_orders(self, request):
        """Получение списка своих ордеров"""
        orders = Order.objects.filter(user=request.user).order_by('-created_at')
        
        # Фильтр по статусу
        status_param = request.query_params.get('status')
        if status_param:
            orders = orders.filter(status=status_param)
        
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated, HasP2PAccess])
    def buy(self, request, pk=None):
        """Покупка по существующему ордеру"""
        order = self.get_object()
        user = request.user
        
        # Проверка, что ордер активен
        if order.status != 'active':
            return Response(
                {"error": "Ордер не активен"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверка, что пользователь не покупает свой же ордер
        if order.user == user:
            return Response(
                {"error": "Вы не можете купить по своему ордеру"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Получаем количество для покупки
        amount_str = request.data.get('amount')
        if not amount_str:
            return Response(
                {"error": "Не указано количество для покупки"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            amount = Decimal(amount_str)
        except:
            return Response(
                {"error": "Некорректное количество"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Проверка количества
        if amount <= 0:
            return Response(
                {"error": "Количество должно быть положительным"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if amount > order.amount:
            return Response(
                {"error": f"Недостаточно средств в ордере. Доступно: {order.amount}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if amount < order.min_amount:
            return Response(
                {"error": f"Минимальная сумма покупки: {order.min_amount}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Рассчитываем стоимость и комиссию
        price = amount * order.price_per_unit
        commission_rate = settings.GAME_SETTINGS.get('P2P_COMMISSION', Decimal('0.03'))
        commission = price * commission_rate
        total_cost = price + commission
        
        # Проверка баланса покупателя при покупке
        if order.type == 'sell':
            if user.ton_balance < total_cost:
                return Response(
                    {"error": f"Недостаточно TON на балансе. Требуется: {total_cost}, доступно: {user.ton_balance}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        else:  # buy order
            token_type = order.token_type
            if token_type == 'CF' and user.cf_balance < amount:
                return Response(
                    {"error": f"Недостаточно CF на балансе. Требуется: {amount}, доступно: {user.cf_balance}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            elif token_type == 'TON' and user.ton_balance < amount:
                return Response(
                    {"error": f"Недостаточно TON на балансе. Требуется: {amount}, доступно: {user.ton_balance}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            elif token_type == 'NOT' and user.not_balance < amount:
                return Response(
                    {"error": f"Недостаточно NOT на балансе. Требуется: {amount}, доступно: {user.not_balance}"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Создаем транзакцию
        if order.type == 'sell':
            buyer = user
            seller = order.user
        else:  # buy order
            buyer = order.user
            seller = user
        
        transaction = Transaction.objects.create(
            order=order,
            buyer=buyer,
            seller=seller,
            amount=amount,
            price_per_unit=order.price_per_unit,
            token_type=order.token_type,
            commission=commission,
            status='pending'
        )
        
        # Обновляем ордер
        order.amount -= amount
        if order.amount == 0:
            order.status = 'completed'
        order.save()
        
        # Возвращаем данные транзакции
        return Response(TransactionSerializer(transaction).data)


class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    API для работы с транзакциями P2P-биржи
    """
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated, IsTransactionParticipant]
    
    def get_queryset(self):
        """Возвращает транзакции текущего пользователя"""
        user = self.request.user
        return Transaction.objects.filter(
            Q(buyer=user) | Q(seller=user)
        ).select_related('order', 'buyer', 'seller').order_by('-created_at')
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def confirm_payment(self, request, pk=None):
        """Подтверждение оплаты покупателем"""
        transaction = self.get_object()
        user = request.user
        
        # Проверка, что пользователь является покупателем
        if transaction.buyer != user:
            return Response(
                {"error": "Только покупатель может подтвердить оплату"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Проверка статуса транзакции
        if transaction.status != 'pending':
            return Response(
                {"error": "Можно подтвердить оплату только для ожидающей транзакции"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Обновляем статус транзакции
        transaction.status = 'paid'
        transaction.save()
        
        return Response(TransactionSerializer(transaction).data)
    
    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def confirm_receipt(self, request, pk=None):
        """Подтверждение получения средств продавцом"""
        transaction = self.get_object()
        user = request.user
        
        # Проверка, что пользователь является продавцом
        if transaction.seller != user:
            return Response(
                {"error": "Только продавец может подтвердить получение средств"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Проверка статуса транзакции
        if transaction.status != 'paid':
            return Response(
                {"error": "Можно подтвердить получение только для оплаченной транзакции"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Обновляем статус транзакции
        transaction.status = 'completed'
        transaction.save()
        
        # Выполняем обмен средствами
        buyer = transaction.buyer
        seller = transaction.seller
        amount = transaction.amount
        price = amount * transaction.price_per_unit
        
        if transaction.token_type == 'CF':
            if transaction.order.type == 'sell':
                # Продавец продает CF, покупатель получает CF
                buyer.cf_balance += amount
                buyer.ton_balance -= price
                seller.ton_balance += price
            else:  # buy order
                # Продавец продает TON за CF, покупатель получает TON
                seller.cf_balance += amount
                seller.ton_balance -= price
                buyer.ton_balance += price
        elif transaction.token_type == 'TON':
            if transaction.order.type == 'sell':
                # Продавец продает TON, покупатель получает TON
                buyer.ton_balance += amount
                buyer.cf_balance -= price  # предполагаем, что TON продается за CF
                seller.cf_balance += price
            else:  # buy order
                # Продавец продает CF за TON, покупатель получает CF
                seller.ton_balance += amount
                seller.cf_balance -= price
                buyer.cf_balance += price
        elif transaction.token_type == 'NOT':
            if transaction.order.type == 'sell':
                # Продавец продает NOT, покупатель получает NOT
                buyer.not_balance += amount
                buyer.ton_balance -= price
                seller.ton_balance += price
            else:  # buy order
                # Продавец продает TON за NOT, покупатель получает TON
                seller.not_balance += amount
                seller.ton_balance -= price
                buyer.ton_balance += price
        
        # Сохраняем изменения
        buyer.save()
        seller.save()
        
        return Response(TransactionSerializer(transaction).data)


class MessageViewSet(viewsets.ModelViewSet):
    """
    API для работы с сообщениями в чате сделки
    """
    serializer_class = MessageSerializer
    permission_classes = [permissions.IsAuthenticated, IsTransactionParticipant]
    
    def get_queryset(self):
        """Возвращает сообщения для конкретной транзакции"""
        transaction_id = self.kwargs.get('transaction_pk')
        return Message.objects.filter(
            transaction_id=transaction_id
        ).select_related('sender').order_by('created_at')
    
    def perform_create(self, serializer):
        """Создание нового сообщения"""
        transaction_id = self.kwargs.get('transaction_pk')
        transaction = Transaction.objects.get(id=transaction_id)
        
        # Проверка, что пользователь является участником транзакции
        user = self.request.user
        if user != transaction.buyer and user != transaction.seller:
            raise permissions.PermissionDenied("Вы не являетесь участником этой сделки")
        
        # Создаем сообщение
        serializer.save(transaction=transaction, sender=user)
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def mark_read(self, request, transaction_pk=None):
        """Отметка всех сообщений как прочитанных"""
        user = request.user
        transaction = Transaction.objects.get(id=transaction_pk)
        
        # Проверка, что пользователь является участником транзакции
        if user != transaction.buyer and user != transaction.seller:
            raise permissions.PermissionDenied("Вы не являетесь участником этой сделки")
        
        # Определяем отправителя сообщений, которые нужно отметить как прочитанные
        sender = transaction.buyer if user == transaction.seller else transaction.seller
        
        # Отмечаем сообщения как прочитанные
        Message.objects.filter(
            transaction=transaction, 
            sender=sender, 
            is_read=False
        ).update(is_read=True)
        
        return Response({"status": "success"}) 