from .models import User, Product, Transaction
from .serializers import UserSerializer, ProductSerializer, TransactionSerializer, UserDetailSerializer
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.utils import timezone
from django.db.models import Q

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    
    def get_permissions(self):
        # 회원가입은 모든 사용자 가능
        if self.action == 'create':
            return [permissions.AllowAny()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == 'create':
            return UserSerializer
        return UserDetailSerializer

    def get_queryset(self):
        # 관리자가 아닌 경우 자신의 정보만 조회 가능
        if not self.request.user.is_staff:
            return User.objects.filter(id=self.request.user.id)
        return User.objects.all()

    @action(detail=True, methods=['get'])
    def sales(self, request, pk=None):
        """판매 내역 조회"""
        user = self.get_object()
        if user != request.user and not request.user.is_staff:
            return Response(
                {"error": "다른 사용자의 판매 내역을 조회할 수 없습니다."},
                status=status.HTTP_403_FORBIDDEN
            )
            permissions.IsAuthenticated
        products = user.products.all()
        serializer = ProductSerializer(products, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def purchases(self, request, pk=None):
        """구매 내역 조회"""
        user = self.get_object()
        if user != request.user and not request.user.is_staff:
            return Response(
                {"error": "다른 사용자의 구매 내역을 조회할 수 없습니다."},
                status=status.HTTP_403_FORBIDDEN
            )
            
        transactions = user.purchases.all()
        serializer = TransactionSerializer(transactions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def change_password(self, request, pk=None):
        """비밀번호 변경"""
        user = self.get_object()
        if user != request.user and not request.user.is_staff:
            return Response(
                {"error": "다른 사용자의 비밀번호를 변경할 수 없습니다."},
                status=status.HTTP_403_FORBIDDEN
            )
            
        serializer = PasswordChangeSerializer(data=request.data)
        if serializer.is_valid():
            if not user.check_password(serializer.validated_data['old_password']):
                return Response(
                    {"error": "현재 비밀번호가 일치하지 않습니다."},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            return Response(status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get('status', None)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        return queryset
    
    @action(detail=True, methods=['post'])
    def purchase(self, request, pk=None):
        """
        제품 구매 신청 API
        """
        product = self.get_object()
        
        # 판매중 상태가 아닌 경우 구매 불가
        if product.status != Product.ProductStatus.ON_SALE:
            return Response(
                {"error": "판매중인 제품만 구매할 수 있습니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 자신의 제품은 구매할 수 없음
        if product.seller == request.user:
            return Response(
                {"error": "자신의 제품은 구매할 수 없습니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 거래 생성 및 제품 상태 변경
        product.status = Product.ProductStatus.RESERVED
        product.save()
        
        Transaction.objects.create(
            product=product,
            seller=product.seller,
            buyer=request.user
        )
        
        return Response(status=status.HTTP_201_CREATED)

class TransactionViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TransactionSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """
        로그인한 사용자의 거래 내역만 조회 가능
        """
        return Transaction.objects.filter(
            Q(seller=self.request.user) | Q(buyer=self.request.user)
        )
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        """
        거래 완료 처리 API (판매자만 가능)
        """
        transaction = self.get_object()
        
        # 판매자만 거래 완료 가능
        if transaction.seller != request.user:
            return Response(
                {"error": "판매자만 거래를 완료할 수 있습니다."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # 이미 완료된 거래는 처리 불가
        if transaction.status == Transaction.TransactionStatus.COMPLETED:
            return Response(
                {"error": "이미 완료된 거래입니다."},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 거래와 제품 상태 변경
        transaction.status = Transaction.TransactionStatus.COMPLETED
        transaction.completed_at = timezone.now()
        transaction.save()
        
        transaction.product.status = Product.ProductStatus.COMPLETED
        transaction.product.save()
        
        return Response(status=status.HTTP_200_OK)