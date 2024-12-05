from rest_framework import serializers
from .models import User, Transaction, Product
from django.contrib.auth.password_validation import validate_password
from django.db.models import Q

# User
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'password2', 'email', 'first_name', 'last_name')
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True}
        }

    def validate(self, attrs):
        # 비밀번호 일치 확인
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "비밀번호가 일치하지 않습니다."})
        return attrs

    def create(self, validated_data):
        # 비밀번호 확인 필드 제거
        validated_data.pop('password2', None)
        # User 생성 (비밀번호 해싱 포함)
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data['first_name'],
            last_name=validated_data['last_name']
        )
        return user

    def update(self, instance, validated_data):
        # 비밀번호 관련 필드 제거
        validated_data.pop('password', None)
        validated_data.pop('password2', None)
        
        # 나머지 필드 업데이트
        return super().update(instance, validated_data)

class UserDetailSerializer(serializers.ModelSerializer):
    products = serializers.SerializerMethodField()
    transactions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'products', 'transactions')
        read_only_fields = ('username',)  # username은 수정 불가

    def get_products(self, obj):
        # 사용자의 판매 중인 제품만 반환
        products = obj.products.filter(status=Product.ProductStatus.ON_SALE)
        return ProductSerializer(products, many=True).data

    def get_transactions(self, obj):
        # 최근 거래 내역 5개만 반환
        transactions = Transaction.objects.filter(
            Q(seller=obj) | Q(buyer=obj)
        ).order_by('-created_at')[:5]
        return TransactionSerializer(transactions, many=True).data
    
# Product
class ProductSerializer(serializers.ModelSerializer):
    seller = UserSerializer(read_only=True)
    
    class Meta:
        model = Product
        fields = ('id', 'seller', 'name', 'price', 'status', 'created_at')
        read_only_fields = ('status',)

    def create(self, validated_data):
        # 제품 생성 시 현재 요청 사용자를 판매자로 지정
        validated_data['seller'] = self.context['request'].user
        return super().create(validated_data)

# Transaction
class TransactionSerializer(serializers.ModelSerializer):
    seller = UserSerializer(read_only=True)
    buyer = UserSerializer(read_only=True)
    product = ProductSerializer(read_only=True)
    
    class Meta:
        model = Transaction
        fields = ('id', 'product', 'seller', 'buyer', 'status', 'created_at', 'completed_at')
        read_only_fields = ('status', 'completed_at')
