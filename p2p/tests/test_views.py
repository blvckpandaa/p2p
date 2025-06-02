from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from decimal import Decimal
import json

from p2p.models import Order, Transaction, Message
from users.models import User

class P2PViewsTest(TestCase):
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
        
        # Создаем пользователя без стейкинга
        self.user_no_access = User.objects.create(
            telegram_id=555555555,
            username='no_access',
            first_name='No',
            last_name='Access',
            cf_balance=1000,
            ton_balance=100,
            not_balance=50
        )
        
        # Создаем тестовые ордера
        self.order1 = Order.objects.create(
            user=self.user1,
            type='sell',
            token_type='CF',
            amount=Decimal('100'),
            price_per_unit=Decimal('10'),
            min_amount=Decimal('10'),
            payment_details='Test payment details',
            status='active',
            expires_at=timezone.now() + timezone.timedelta(days=3)
        )
        
        self.order2 = Order.objects.create(
            user=self.user2,
            type='buy',
            token_type='TON',
            amount=Decimal('50'),
            price_per_unit=Decimal('15'),
            min_amount=Decimal('5'),
            payment_details='Test payment details for buy order',
            status='active',
            expires_at=timezone.now() + timezone.timedelta(days=3)
        )
        
        # Настраиваем клиенты для имитации запросов
        self.client1 = Client()
        self.client2 = Client()
        self.client_no_access = Client()
        
        # Имитируем аутентификацию пользователей
        self.client1.force_login(self.user1)
        self.client2.force_login(self.user2)
        self.client_no_access.force_login(self.user_no_access)
    
    def test_p2p_market_view(self):
        """Тест отображения страницы P2P-биржи"""
        response = self.client1.get(reverse('p2p:market'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'p2p/market.html')
        
        # Проверяем наличие ордеров в контексте
        self.assertTrue('orders' in response.context)
        self.assertEqual(len(response.context['orders']), 2)
    
    def test_create_order_view(self):
        """Тест создания нового ордера"""
        data = {
            'type': 'buy',
            'token_type': 'CF',
            'amount': '20',
            'price_per_unit': '12',
            'min_amount': '5',
            'payment_details': 'New test payment details'
        }
        
        response = self.client1.post(reverse('p2p:create_order'), data)
        
        # Должно быть перенаправление на страницу с ордерами
        self.assertRedirects(response, reverse('p2p:market'))
        
        # Проверяем, что ордер создан в базе данных
        self.assertEqual(Order.objects.count(), 3)
        new_order = Order.objects.latest('created_at')
        self.assertEqual(new_order.type, 'buy')
        self.assertEqual(new_order.token_type, 'CF')
        self.assertEqual(new_order.amount, Decimal('20'))
        self.assertEqual(new_order.price_per_unit, Decimal('12'))
        self.assertEqual(new_order.user, self.user1)
    
    def test_order_detail_view(self):
        """Тест отображения деталей ордера"""
        response = self.client2.get(reverse('p2p:order_detail', args=[self.order1.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'p2p/order_detail.html')
        self.assertEqual(response.context['order'], self.order1)
    
    def test_buy_order_view(self):
        """Тест покупки по существующему ордеру"""
        data = {
            'amount': '50'  # Покупаем половину от доступного количества
        }
        
        response = self.client2.post(reverse('p2p:buy_order', args=[self.order1.id]), data)
        
        # Должно быть перенаправление на страницу сделки
        transaction = Transaction.objects.latest('created_at')
        self.assertRedirects(response, reverse('p2p:transaction_detail', args=[transaction.id]))
        
        # Проверяем, что транзакция создана корректно
        self.assertEqual(transaction.order, self.order1)
        self.assertEqual(transaction.buyer, self.user2)
        self.assertEqual(transaction.seller, self.user1)
        self.assertEqual(transaction.amount, Decimal('50'))
        self.assertEqual(transaction.price_per_unit, Decimal('10'))
        self.assertEqual(transaction.token_type, 'CF')
        
        # Проверяем, что ордер обновлен (его количество уменьшилось)
        self.order1.refresh_from_db()
        self.assertEqual(self.order1.amount, Decimal('50'))  # Было 100, стало 50
        
        # Если весь ордер выкупили, он должен быть отмечен как выполненный
        data = {
            'amount': '50'  # Покупаем оставшуюся часть
        }
        
        response = self.client2.post(reverse('p2p:buy_order', args=[self.order1.id]), data)
        self.order1.refresh_from_db()
        self.assertEqual(self.order1.status, 'completed')
    
    def test_my_orders_view(self):
        """Тест отображения собственных ордеров пользователя"""
        response = self.client1.get(reverse('p2p:my_orders'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'p2p/my_orders.html')
        
        # Проверяем, что в контексте только ордера текущего пользователя
        self.assertTrue('orders' in response.context)
        self.assertEqual(len(response.context['orders']), 1)
        self.assertEqual(response.context['orders'][0], self.order1)
    
    def test_my_transactions_view(self):
        """Тест отображения сделок пользователя"""
        # Создаем тестовую транзакцию
        transaction = Transaction.objects.create(
            order=self.order1,
            buyer=self.user2,
            seller=self.user1,
            amount=Decimal('20'),
            price_per_unit=Decimal('10'),
            token_type='CF',
            status='completed'
        )
        
        # Проверяем отображение для продавца
        response = self.client1.get(reverse('p2p:my_transactions'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'p2p/my_transactions.html')
        self.assertTrue('transactions' in response.context)
        self.assertEqual(len(response.context['transactions']), 1)
        
        # Проверяем отображение для покупателя
        response = self.client2.get(reverse('p2p:my_transactions'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['transactions']), 1)
    
    def test_transaction_detail_view(self):
        """Тест отображения деталей сделки"""
        # Создаем тестовую транзакцию
        transaction = Transaction.objects.create(
            order=self.order1,
            buyer=self.user2,
            seller=self.user1,
            amount=Decimal('20'),
            price_per_unit=Decimal('10'),
            token_type='CF',
            status='pending'
        )
        
        # Проверяем доступ для продавца
        response = self.client1.get(reverse('p2p:transaction_detail', args=[transaction.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'p2p/transaction_detail.html')
        self.assertEqual(response.context['transaction'], transaction)
        
        # Проверяем доступ для покупателя
        response = self.client2.get(reverse('p2p:transaction_detail', args=[transaction.id]))
        self.assertEqual(response.status_code, 200)
        
        # Проверяем недоступность для других пользователей
        response = self.client_no_access.get(reverse('p2p:transaction_detail', args=[transaction.id]))
        self.assertEqual(response.status_code, 403)  # Forbidden
    
    def test_cancel_order_view(self):
        """Тест отмены ордера"""
        response = self.client1.post(reverse('p2p:cancel_order', args=[self.order1.id]))
        
        # Должно быть перенаправление на страницу с ордерами
        self.assertRedirects(response, reverse('p2p:my_orders'))
        
        # Проверяем, что ордер отменен
        self.order1.refresh_from_db()
        self.assertEqual(self.order1.status, 'cancelled')
    
    def test_confirm_payment_view(self):
        """Тест подтверждения оплаты покупателем"""
        # Создаем тестовую транзакцию
        transaction = Transaction.objects.create(
            order=self.order1,
            buyer=self.user2,
            seller=self.user1,
            amount=Decimal('20'),
            price_per_unit=Decimal('10'),
            token_type='CF',
            status='pending'
        )
        
        # Покупатель подтверждает оплату
        response = self.client2.post(reverse('p2p:confirm_payment', args=[transaction.id]))
        
        # Должно быть перенаправление на страницу сделки
        self.assertRedirects(response, reverse('p2p:transaction_detail', args=[transaction.id]))
        
        # Проверяем, что статус транзакции обновлен
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, 'paid')
    
    def test_confirm_receipt_view(self):
        """Тест подтверждения получения средств продавцом"""
        # Создаем тестовую транзакцию со статусом 'paid'
        transaction = Transaction.objects.create(
            order=self.order1,
            buyer=self.user2,
            seller=self.user1,
            amount=Decimal('20'),
            price_per_unit=Decimal('10'),
            token_type='CF',
            status='paid'
        )
        
        # Продавец подтверждает получение средств
        response = self.client1.post(reverse('p2p:confirm_receipt', args=[transaction.id]))
        
        # Должно быть перенаправление на страницу сделки
        self.assertRedirects(response, reverse('p2p:transaction_detail', args=[transaction.id]))
        
        # Проверяем, что статус транзакции обновлен на 'completed'
        transaction.refresh_from_db()
        self.assertEqual(transaction.status, 'completed')
    
    def test_send_message_view(self):
        """Тест отправки сообщений в чате сделки"""
        # Создаем тестовую транзакцию
        transaction = Transaction.objects.create(
            order=self.order1,
            buyer=self.user2,
            seller=self.user1,
            amount=Decimal('20'),
            price_per_unit=Decimal('10'),
            token_type='CF',
            status='pending'
        )
        
        # Продавец отправляет сообщение
        data = {
            'content': 'Hello from seller'
        }
        
        response = self.client1.post(reverse('p2p:send_message', args=[transaction.id]), data)
        
        # Должно быть перенаправление на страницу сделки
        self.assertRedirects(response, reverse('p2p:transaction_detail', args=[transaction.id]))
        
        # Проверяем, что сообщение создано
        self.assertEqual(Message.objects.count(), 1)
        message = Message.objects.first()
        self.assertEqual(message.content, 'Hello from seller')
        self.assertEqual(message.sender, self.user1)
        
        # Покупатель отправляет сообщение
        data = {
            'content': 'Hello from buyer'
        }
        
        response = self.client2.post(reverse('p2p:send_message', args=[transaction.id]), data)
        self.assertRedirects(response, reverse('p2p:transaction_detail', args=[transaction.id]))
        
        # Проверяем, что второе сообщение создано
        self.assertEqual(Message.objects.count(), 2)
        message = Message.objects.latest('created_at')
        self.assertEqual(message.content, 'Hello from buyer')
        self.assertEqual(message.sender, self.user2)
    
    def test_access_control(self):
        """Тест контроля доступа к P2P-бирже"""
        # Пользователь без стейкинга должен быть перенаправлен на страницу с информацией о блокировке
        response = self.client_no_access.get(reverse('p2p:market'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'p2p/locked.html')
        
        # Пользователь не должен иметь возможности создавать ордера
        data = {
            'type': 'buy',
            'token_type': 'CF',
            'amount': '20',
            'price_per_unit': '12',
            'min_amount': '5',
            'payment_details': 'New test payment details'
        }
        
        response = self.client_no_access.post(reverse('p2p:create_order'), data)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'p2p/locked.html')
        
        # Проверяем, что новый ордер не был создан
        self.assertEqual(Order.objects.count(), 2) 