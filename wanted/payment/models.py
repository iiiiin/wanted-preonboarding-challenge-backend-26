from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from decimal import Decimal

class User(AbstractUser):
    class Meta:
        db_table = 'users'
        indexes = [
            models.Index(fields=['username'])
        ]

class Product(models.Model):
    """
    제품 모델
    판매자가 등록한 제품 정보를 저장합니다.
    """
    class ProductStatus(models.TextChoices):
        ON_SALE = '판매중', '판매중'
        RESERVED = '예약중', '예약중'
        COMPLETED = '완료', '완료'

    seller = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='products',
        verbose_name='판매자'
    )
    name = models.CharField(
        max_length=100,
        verbose_name='제품명'
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        verbose_name='가격'
    )
    status = models.CharField(
        max_length=20,
        choices=ProductStatus.choices,
        default=ProductStatus.ON_SALE,
        verbose_name='상태'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='등록일시'
    )

    class Meta:
        db_table = 'products'
        indexes = [
            models.Index(fields=['seller']),
            models.Index(fields=['status'])
        ]

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"

class Transaction(models.Model):
    """
    거래 모델
    제품 거래 정보를 저장합니다.
    """
    class TransactionStatus(models.TextChoices):
        IN_PROGRESS = '진행중', '진행중'
        COMPLETED = '완료', '완료'

    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,  # 거래 기록은 보존하기 위해 PROTECT 사용
        related_name='transactions',
        verbose_name='제품'
    )
    seller = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='sales',
        verbose_name='판매자'
    )
    buyer = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name='purchases',
        verbose_name='구매자'
    )
    status = models.CharField(
        max_length=20,
        choices=TransactionStatus.choices,
        default=TransactionStatus.IN_PROGRESS,
        verbose_name='거래상태'
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='거래시작일시'
    )
    completed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name='거래완료일시'
    )

    class Meta:
        db_table = 'transactions'
        indexes = [
            models.Index(fields=['seller', 'buyer']),
            models.Index(fields=['product'])
        ]

    def __str__(self):
        return f"거래 #{self.id} - {self.product.name}"
