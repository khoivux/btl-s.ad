from django.urls import path
from app.views.books import BookListView, BookSearchView, BookDetailView, BookReviewSubmitView
from app.views.customer import LoginView, RegisterView, LogoutView, ProfileView, ProfileApiView, AddressApiListView, AddressApiDetailView, PointTransactionApiView, ChatHistoryApiView, ChatConsultantApiView
from app.views.orders import CheckoutPageView, CheckoutApiView, OrderHistoryView, OrderSuccessView, OrderDetailView, OrderTrackingView, OrderActionApiView, OrderDetailApiView
from app.views.cart import CartView, AddCartItemView, ModifyCartItemView
from app.views.vouchers import WalletApiView, VouchersListApiView, MembershipLevelsApiView, RedeemVoucherApiView, CustomerVouchersApiView, VouchersShopView, VoucherDetailApiView
from app.views.staff import StaffLoginView, StaffDashboardView, StaffLogoutView, StaffBookAddView, StaffBookModifyView, StaffVoucherListCreateView, StaffVoucherDetailView, StaffCategoryAddView, StaffCategoryModifyView, StaffOrderManageView
from app.views.shipper import ShipperDashboardView, ShipperShipmentsApiView, ShipperStatusUpdateApiView

urlpatterns = [
    # Book routes
    path('', BookListView.as_view(), name='home'),
    path('books/', BookListView.as_view(), name='book_list'),
    path('books/<int:book_id>/', BookDetailView.as_view(), name='book_detail'),
    path('api/books/<int:book_id>/reviews/', BookReviewSubmitView.as_view(), name='book_review_submit'),
    path('search/', BookSearchView.as_view(), name='search'),

    # Auth & Customer
    path('login/', LoginView.as_view(), name='login'),
    path('register/', RegisterView.as_view(), name='register'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('api/profile/', ProfileApiView.as_view(), name='api_update_profile'),
    path('api/loyalty/transactions/', PointTransactionApiView.as_view(), name='api_point_transactions'),

    # AI Assistant
    path('api/chat/history/', ChatHistoryApiView.as_view(), name='api_chat_history'),
    path('api/chat/consultant/', ChatConsultantApiView.as_view(), name='api_chat_consultant'),

    # Address API
    path('api/addresses/<int:customer_id>/', AddressApiListView.as_view(), name='address_list'),
    path('api/addresses/<int:customer_id>/<int:pk>/', AddressApiDetailView.as_view(), name='address_detail'),

    # Cart routines
    path('carts/<int:customer_id>/', CartView.as_view(), name='view_cart'),
    path('api/carts/items/', AddCartItemView.as_view(), name='add_cart_item'),
    path('api/carts/items/<int:item_id>/', ModifyCartItemView.as_view(), name='modify_cart_item'),

    # Checkout & Orders
    path('checkout/', CheckoutPageView.as_view(), name='checkout_page'),
    path('api/checkout/', CheckoutApiView.as_view(), name='checkout'),
    path('orders/', OrderHistoryView.as_view(), name='order_history'),
    path('orders/<int:order_id>/success/', OrderSuccessView.as_view(), name='order_success'),
    path('orders/<int:order_id>/detail/', OrderDetailView.as_view(), name='order_detail'),
    path('orders/<int:order_id>/tracking/', OrderTrackingView.as_view(), name='order_tracking'),
    path('api/orders/<int:order_id>/detail/', OrderDetailApiView.as_view(), name='api_order_detail'),
    path('api/orders/<int:order_id>/cancel/', OrderActionApiView.as_view(), kwargs={'action': 'cancel'}, name='api_cancel_order'),
    path('api/orders/<int:order_id>/delete/', OrderActionApiView.as_view(), kwargs={'action': 'delete'}, name='api_delete_order'),

    # Loyalty & Vouchers
    path('api/loyalty/wallet/', WalletApiView.as_view(), name='api_wallet_detail'),
    path('api/vouchers/', VouchersListApiView.as_view(), name='api_vouchers_list'),
    path('api/vouchers/<str:code>/', VoucherDetailApiView.as_view(), name='api_voucher_detail'),
    path('api/vouchers/redeem/', RedeemVoucherApiView.as_view(), name='api_redeem_voucher'),
    path('api/vouchers/customer/', CustomerVouchersApiView.as_view(), name='api_customer_vouchers'),
    path('api/membership-levels/', MembershipLevelsApiView.as_view(), name='api_membership_levels'),
    path('vouchers/shop/', VouchersShopView.as_view(), name='vouchers_shop'),

    # Staff routes
    path('staff/login/', StaffLoginView.as_view(), name='staff_login'),
    path('staff/dashboard/', StaffDashboardView.as_view(), name='staff_dashboard'),
    path('staff/logout/', StaffLogoutView.as_view(), name='staff_logout'),
    path('staff/books/add/', StaffBookAddView.as_view(), name='staff_add_book'),
    path('staff/books/<int:pk>/update/', StaffBookModifyView.as_view(), name='staff_update_book'),
    path('staff/books/<int:pk>/delete/', StaffBookModifyView.as_view(), name='staff_delete_book'),
    path('staff/categories/add/', StaffCategoryAddView.as_view(), name='staff_add_category'),
    path('staff/categories/<int:pk>/update/', StaffCategoryModifyView.as_view(), name='staff_update_category'),
    path('staff/categories/<int:pk>/delete/', StaffCategoryModifyView.as_view(), name='staff_delete_category'),

    # Staff Voucher management
    path('api/staff/vouchers/', StaffVoucherListCreateView.as_view(), name='staff_voucher_list_create'),
    path('api/staff/vouchers/<int:pk>/', StaffVoucherDetailView.as_view(), name='staff_voucher_detail'),

    # Staff Order management (RESTful)
    path('api/staff/orders/', StaffOrderManageView.as_view(), name='staff_order_list'),
    path('api/staff/orders/<int:pk>/', StaffOrderManageView.as_view(), name='staff_order_manage'),

    # Shipper routes
    path('shipper/dashboard/', ShipperDashboardView.as_view(), name='shipper_dashboard'),
    path('api/shipper/shipments/<str:filter_type>/', ShipperShipmentsApiView.as_view(), name='api_shipper_shipments'),
    path('api/shipper/shipments/<int:pk>/status/', ShipperStatusUpdateApiView.as_view(), name='api_shipper_status_update'),
]
