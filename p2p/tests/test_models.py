from django.test import TestCase
from django.utils import timezone
from decimal import Decimal
from p2p.models import Order, Transaction, Message
from users.models import User

class OrderModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            telegram_id=123456789,
            username='testuser',
            first_name='Test',
            last_name='User',
            cf_balance=1000,
            ton_balance=100,
            not_balance=50
        )
        
        self.order = Order.objects.create(
            user=self.user,
            type='sell',
            token_type='CF',
            amount=Decimal('100'),
            price_per_unit=Decimal('10'),
            min_amount=Decimal('10'),
            payment_details='Test payment details',
            status='active',
            expires_at=timezone.now() + timezone.timedelta(days=3)
        )
    
    def test_order_creation(self):
        """Тест создания ордера"""
        self.assertEqual(self.order.user, self.user)
        self.assertEqual(self.order.type, 'sell')
        self.assertEqual(self.order.token_type, 'CF')
        self.assertEqual(self.order.amount, Decimal('100'))
        self.assertEqual(self.order.price_per_unit, Decimal('10'))
        self.assertEqual(self.order.min_amount, Decimal('10'))
        self.assertEqual(self.order.payment_details, 'Test payment details')
        self.assertEqual(self.order.status, 'active')
    
    def test_order_str_method(self):
        """Тест строкового представления ордера"""
        expected_str = f"{self.order.type.upper()} {self.order.amount} {self.order.token_type} at {self.order.price_per_unit} TON"
        self.assertEqual(str(self.order), expected_str)
    
    def test_order_total_price(self):
        """Тест расчета полной стоимости ордера"""
        self.assertEqual(self.order.total_price, Decimal('1000'))  # 100 * 10
    
    def test_is_expired(self):
        """Тест проверки истечения срока ордера"""
        # Ордер не должен быть просрочен
        self.assertFalse(self.order.is_expired)
        
        # Меняем дату истечения на прошедшую
        self.order.expires_at = timezone.now() - timezone.timedelta(days=1)
        self.order.save()
        
        # Теперь ордер должен быть просрочен
        self.assertTrue(self.order.is_expired)


class TransactionModelTest(TestCase):
    def setUp(self):
        self.seller = User.objects.create(
            telegram_id=123456789,
            username='seller',
            first_name='Seller',
            last_name='User',
            cf_balance=1000,
            ton_balance=100,
            not_balance=50
        )
        
        self.buyer = User.objects.create(
            telegram_id=987654321,
            username='buyer',
            first_name='Buyer',
            last_name='User',
            cf_balance=500,
            ton_balance=200,
            not_balance=50
        )
        
        self.order = Order.objects.create(
            user=self.seller,
            type='sell',
            token_type='CF',
            amount=Decimal('100'),
            price_per_unit=Decimal('10'),
            min_amount=Decimal('10'),
            payment_details='Test payment details',
            status='active',
            expires_at=timezone.now() + timezone.timedelta(days=3)
        )
        
        self.transaction = Transaction.objects.create(
            order=self.order,
            buyer=self.buyer,
            seller=self.seller,
            amount=Decimal('50'),
            price_per_unit=Decimal('10'),
            token_type='CF',
            commission=Decimal('15'),
            status='pending'
        )
    
    def test_transaction_creation(self):
        """Тест создания транзакции"""
        self.assertEqual(self.transaction.order, self.order)
        self.assertEqual(self.transaction.buyer, self.buyer)
        self.assertEqual(self.transaction.seller, self.seller)
        self.assertEqual(self.transaction.amount, Decimal('50'))
        self.assertEqual(self.transaction.price_per_unit, Decimal('10'))
        self.assertEqual(self.transaction.token_type, 'CF')
        self.assertEqual(self.transaction.commission, Decimal('15'))
        self.assertEqual(self.transaction.status, 'pending')
    
    def test_transaction_str_method(self):
        """Тест строкового представления транзакции"""
        expected_str = f"Transaction {self.transaction.id}: {self.transaction.amount} {self.transaction.token_type}"
        self.assertEqual(str(self.transaction), expected_str)
    
    def test_transaction_total_price(self):
        """Тест расчета полной стоимости транзакции"""
        self.assertEqual(self.transaction.total_price, Decimal('500'))  # 50 * 10
    
    def test_transaction_total_with_commission(self):
        """Тест расчета полной стоимости транзакции с комиссией"""
        self.assertEqual(self.transaction.total_with_commission, Decimal('515'))  # 500 + 15


class MessageModelTest(TestCase):
    def setUp(self):
        self.seller = User.objects.create(
            telegram_id=123456789,
            username='seller',
            first_name='Seller',
            last_name='User',
            cf_balance=1000,
            ton_balance=100,
            not_balance=50
        )
        
        self.buyer = User.objects.create(
            telegram_id=987654321,
            username='buyer',
            first_name='Buyer',
            last_name='User',
            cf_balance=500,
            ton_balance=200,
            not_balance=50
        )
        
        self.order = Order.objects.create(
            user=self.seller,
            type='sell',
            token_type='CF',
            amount=Decimal('100'),
            price_per_unit=Decimal('10'),
            min_amount=Decimal('10'),
            payment_details='Test payment details',
            status='active',
            expires_at=timezone.now() + timezone.timedelta(days=3)
        )
        
        self.transaction = Transaction.objects.create(
            order=self.order,
            buyer=self.buyer,
            seller=self.seller,
            amount=Decimal('50'),
            price_per_unit=Decimal('10'),
            token_type='CF',
            commission=Decimal('15'),
            status='pending'
        )
        
        self.message = Message.objects.create(
            transaction=self.transaction,
            sender=self.seller,
            content='Test message',
            is_read=False
        )
    
    def test_message_creation(self):
        """Тест создания сообщения"""
        self.assertEqual(self.message.transaction, self.transaction)
        self.assertEqual(self.message.sender, self.seller)
        self.assertEqual(self.message.content, 'Test message')
        self.assertFalse(self.message.is_read)
    
    def test_message_str_method(self):
        """Тест строкового представления сообщения"""
        expected_str = f"Message from {self.seller.username}: {self.message.content[:20]}"
        self.assertEqual(str(self.message), expected_str)
    
    def test_recipient(self):
        """Тест определения получателя сообщения"""
        # Если отправитель - продавец, получателем должен быть покупатель
        self.assertEqual(self.message.recipient, self.buyer)
        
        # Создаем сообщение от покупателя
        buyer_message = Message.objects.create(
            transaction=self.transaction,
            sender=self.buyer,
            content='Reply from buyer',
            is_read=False
        )
        
        # Если отправитель - покупатель, получателем должен быть продавец
        self.assertEqual(buyer_message.recipient, self.seller) 