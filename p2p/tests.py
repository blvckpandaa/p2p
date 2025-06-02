from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from decimal import Decimal
from .models import Order, Transaction, Message
from users.models import User
import json

class P2PTestCase(TestCase):
    def setUp(self):
        # Создаем тестовых пользователей
        self.user1 = User.objects.create(
            telegram_id=123456789,
            username='user1',
            first_name='User',
            last_name='One',
            cf_balance=1000,
            ton_balance=100,
            not_balance=50,
            staking_until=timezone.now() + timezone.timedelta(days=10)  # Чтобы был доступ к P2P
        )
        
        self.user2 = User.objects.create(
            telegram_id=987654321,
            username='user2',
            first_name='User',
            last_name='Two',
            cf_balance=1000,
            ton_balance=100,
            not_balance=50,
            staking_until=timezone.now() + timezone.timedelta(days=10)  # Чтобы был доступ к P2P
        )
        
        # Создаем тестовый ордер
        self.order = Order.objects.create(
            user=self.user1,
            type='sell',
            token_type='CF',
            amount=Decimal('100'),
            price_per_unit=Decimal('10'),
            min_amount=Decimal('100'),
            payment_details='Test payment details',
            status='active',
            expires_at=timezone.now() + timezone.timedelta(days=3)
        )
        
        # Настраиваем клиенты для имитации запросов
        self.client1 = Client()
        self.client2 = Client()
        
        # Имитируем аутентификацию пользователей
        self.client1.force_login(self.user1)
        self.client2.force_login(self.user2)
    
    def test_p2p_market_view(self):
        """Тест отображения страницы P2P-биржи"""
        response = self.client1.get(reverse('p2p_market'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'p2p/index.html')
        
        # Проверяем наличие ордера в контексте
        self.assertIn('orders', response.context)
        self.assertEqual(len(response.context['orders']), 1)
    
    def test_order_detail_view(self):
        """Тест отображения деталей ордера"""
        response = self.client2.get(reverse('order_detail', args=[self.order.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'p2p/order_detail.html')
        self.assertEqual(response.context['order'], self.order)
    
    def test_create_order(self):
        """Тест создания нового ордера"""
        data = {
            'type': 'buy',
            'token_type': 'TON',
            'amount': '10',
            'price': '15',
            'min_amount': '150',
            'payment_details': 'Test buy order details'
        }
        
        response = self.client1.post(
            reverse('create_order'),
            data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['status'], 'success')
        
        # Проверяем, что ордер создан в базе данных
        self.assertEqual(Order.objects.count(), 2)
        new_order = Order.objects.get(type='buy', token_type='TON')
        self.assertEqual(new_order.amount, Decimal('10'))
        self.assertEqual(new_order.price_per_unit, Decimal('15'))
    
    def test_buy_order(self):
        """Тест покупки по существующему ордеру"""
        # Сохраняем начальные балансы
        initial_seller_cf = self.user1.cf_balance
        initial_buyer_cf = self.user2.cf_balance
        initial_buyer_ton = self.user2.ton_balance
        
        # Выполняем покупку
        response = self.client2.post(
            reverse('buy_order', args=[self.order.id]),
            {},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['status'], 'success')
        
        # Проверяем, что ордер отмечен как завершенный
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'completed')
        
        # Проверяем, что создана транзакция
        self.assertEqual(Transaction.objects.count(), 1)
        tx = Transaction.objects.first()
        self.assertEqual(tx.buyer, self.user2)
        self.assertEqual(tx.seller, self.user1)
        self.assertEqual(tx.amount, Decimal('100'))
        
        # Проверяем, что балансы изменились правильно
        self.user1.refresh_from_db()
        self.user2.refresh_from_db()
        
        # У покупателя должно быть списано TON и начислено CF
        self.assertEqual(self.user2.cf_balance, initial_buyer_cf + Decimal('100'))
        
        # Проверяем комиссию
        commission_rate = settings.GAME_SETTINGS.get('P2P_COMMISSION', Decimal('0.03'))
        expected_commission = Decimal('100') * Decimal('10') * commission_rate
        self.assertAlmostEqual(
            self.user2.ton_balance, 
            initial_buyer_ton - (Decimal('100') * Decimal('10') + expected_commission)
        )
        
        # У продавца должно быть начислено TON
        self.assertEqual(self.user1.ton_balance, Decimal('100') + Decimal('100') * Decimal('10'))
    
    def test_toggle_order(self):
        """Тест активации/деактивации ордера"""
        # Деактивируем ордер
        response = self.client1.post(
            reverse('toggle_order'),
            {'order_id': self.order.id},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['status'], 'success')
        
        # Проверяем, что ордер деактивирован
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'cancelled')
        
        # Проверяем, что токены возвращены на баланс
        self.user1.refresh_from_db()
        self.assertEqual(self.user1.cf_balance, Decimal('1000') + Decimal('100'))
        
        # Активируем ордер обратно
        response = self.client1.post(
            reverse('toggle_order'),
            {'order_id': self.order.id},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        
        # Проверяем, что ордер активирован
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'active')
        
        # Проверяем, что токены списаны с баланса снова
        self.user1.refresh_from_db()
        self.assertEqual(self.user1.cf_balance, Decimal('1000'))
    
    def test_send_message(self):
        """Тест отправки сообщений в чате"""
        # Создаем транзакцию для сообщений
        transaction = Transaction.objects.create(
            order=self.order,
            buyer=self.user2,
            seller=self.user1,
            amount=Decimal('50'),
            price_per_unit=Decimal('10'),
            token_type='CF',
            commission=Decimal('15')
        )
        
        # Отправляем сообщение
        response = self.client1.post(
            reverse('send_message', args=[transaction.id]),
            {'content': 'Test message from seller'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['status'], 'success')
        
        # Проверяем, что сообщение создано в базе данных
        self.assertEqual(Message.objects.count(), 1)
        message = Message.objects.first()
        self.assertEqual(message.content, 'Test message from seller')
        self.assertEqual(message.sender, self.user1)
        
        # Проверяем отображение сообщения на странице сделки
        response = self.client2.get(reverse('deal_detail', args=[transaction.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'p2p/deal_detail.html')
        self.assertContains(response, 'Test message from seller')
        
        # Проверяем, что сообщение отмечается как прочитанное
        message.refresh_from_db()
        self.assertTrue(message.is_read)
    
    def test_access_control(self):
        """Тест контроля доступа к P2P-бирже"""
        # Создаем пользователя без стейкинга
        user_no_access = User.objects.create(
            telegram_id=555555555,
            username='no_access',
            first_name='No',
            last_name='Access',
            cf_balance=1000,
            ton_balance=100,
            not_balance=50
        )
        
        client = Client()
        client.force_login(user_no_access)
        
        # Пользователь без стейкинга должен быть перенаправлен на страницу с информацией о блокировке
        response = client.get(reverse('p2p_market'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'p2p/locked.html')
        
        # Пользователь не должен иметь возможности создавать ордера
        data = {
            'type': 'buy',
            'token_type': 'CF',
            'amount': '10',
            'price': '15',
            'min_amount': '150',
            'payment_details': 'Test details'
        }
        
        response = client.post(
            reverse('create_order'),
            data,
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['status'], 'error')
        self.assertEqual(response_data['message'], 'Доступ к бирже закрыт')
