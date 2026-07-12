from django.contrib import admin
from .models import Group, GroupMembership, Expense, ExpenseSplit, Payment


class MembershipInline(admin.TabularInline):
    model = GroupMembership
    extra = 1


@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    list_display = ["name", "default_currency", "created_by", "created_at"]
    inlines = [MembershipInline]


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ["description", "group", "paid_by", "amount", "currency", "date", "split_type"]
    list_filter = ["group", "currency", "split_type"]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["from_member", "to_member", "amount_inr", "date", "group"]
    list_filter = ["group"]
