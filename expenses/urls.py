from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import GroupViewSet, ExpenseViewSet, PaymentViewSet

router = DefaultRouter()
router.register(r"groups", GroupViewSet, basename="group")

urlpatterns = [
    path("", include(router.urls)),
    path(
        "groups/<int:group_pk>/expenses/",
        ExpenseViewSet.as_view({"get": "list", "post": "create"}),
        name="group-expenses",
    ),
    path(
        "groups/<int:group_pk>/expenses/<int:pk>/",
        ExpenseViewSet.as_view({"get": "retrieve", "put": "update", "delete": "destroy"}),
        name="group-expense-detail",
    ),
    path(
        "groups/<int:group_pk>/payments/",
        PaymentViewSet.as_view({"get": "list", "post": "create"}),
        name="group-payments",
    ),
]
