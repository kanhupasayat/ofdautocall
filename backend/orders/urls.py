from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    ReadyToDispatchView,
    InTransitView,
    TrackOrderView,
    TodayOrdersView,
    OFDOrdersView,
    MakeCallView,
    CallHistoryView,
    SchedulerControlView,
    VAPIWebhookView,
    CleanupDeliveredView,
    PollCallStatusView
)
from .auth_views import (
    RegisterView,
    LoginView,
    LogoutView,
    UserProfileView
)

urlpatterns = [
    # Authentication endpoints
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/profile/', UserProfileView.as_view(), name='user-profile'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),

    # Orders endpoints (require authentication)
    path('orders/today/', TodayOrdersView.as_view(), name='today-orders'),
    path('orders/ready-to-dispatch/', ReadyToDispatchView.as_view(), name='ready-to-dispatch'),
    path('orders/in-transit/', InTransitView.as_view(), name='in-transit'),
    path('orders/ofd/', OFDOrdersView.as_view(), name='ofd-orders'),
    path('orders/track/', TrackOrderView.as_view(), name='track-order'),
    path('orders/make-call/', MakeCallView.as_view(), name='make-call'),
    path('orders/call-history/', CallHistoryView.as_view(), name='call-history'),
    path('orders/scheduler/', SchedulerControlView.as_view(), name='scheduler-control'),
    path('orders/cleanup-delivered/', CleanupDeliveredView.as_view(), name='cleanup-delivered'),
    path('orders/poll-call-status/', PollCallStatusView.as_view(), name='poll-call-status'),

    # Public endpoints (no auth required)
    path('orders/vapi-webhook/', VAPIWebhookView.as_view(), name='vapi-webhook'),
]

