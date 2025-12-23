from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum, Count, Min

from .models import Customer, Product, Article, Order, OrderItem, ShippingAddress


# -----------------------------
# Global admin branding (optional)
# -----------------------------
admin.site.site_header = "HomeClick Administration"
admin.site.site_title = "HomeClick Admin"
admin.site.index_title = "Admin Dashboard"


# -----------------------------
# Inlines
# -----------------------------
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    autocomplete_fields = ["product"]
    fields = ("product", "quantity", "line_total")
    readonly_fields = ("line_total",)

    @admin.display(description="Line total (VNĐ)")
    def line_total(self, obj: OrderItem):
        try:
            return f"{int(obj.get_total):,}"
        except Exception:
            return "0"


class ShippingAddressInline(admin.StackedInline):
    model = ShippingAddress
    extra = 0
    can_delete = True
    fields = ("address", "city", "state", "mobile", "date_added")
    readonly_fields = ("date_added",)


# -----------------------------
# Admin actions
# -----------------------------
@admin.action(description="Mark selected orders as COMPLETE")
def mark_complete(modeladmin, request, queryset):
    queryset.update(complete=True)


@admin.action(description="Mark selected orders as INCOMPLETE")
def mark_incomplete(modeladmin, request, queryset):
    queryset.update(complete=False)


@admin.action(description="Merge duplicate items in selected orders (same product)")
def merge_duplicate_items(modeladmin, request, queryset):
    """
    Nếu trong 1 order có nhiều OrderItem trùng product (do add nhanh),
    action này sẽ gộp lại thành 1 dòng: quantity = tổng quantity.
    """
    for order in queryset:
        dup_groups = (
            OrderItem.objects
            .filter(order=order)
            .values("product_id")
            .annotate(cnt=Count("id"), total_qty=Sum("quantity"), keep_id=Min("id"))
            .filter(cnt__gt=1)
        )
        for g in dup_groups:
            keep_id = g["keep_id"]
            total_qty = g["total_qty"] or 0

            OrderItem.objects.filter(id=keep_id).update(quantity=total_qty)
            OrderItem.objects.filter(order=order, product_id=g["product_id"]).exclude(id=keep_id).delete()


# -----------------------------
# ModelAdmins
# -----------------------------
@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "name", "email", "phone_number", "address")
    search_fields = ("name", "email", "user__username", "phone_number", "address")
    list_per_page = 25


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("id", "image_preview", "name", "code", "price_vnd", "digital")
    search_fields = ("name", "code")
    list_filter = ("digital",)
    ordering = ("name",)
    list_per_page = 25

    @admin.display(description="Price (VNĐ)")
    def price_vnd(self, obj: Product):
        try:
            return f"{int(obj.price):,}"
        except Exception:
            return "0"

    @admin.display(description="Image")
    def image_preview(self, obj: Product):
        if obj.image:
            return format_html(
                '<img src="{}" style="width:56px;height:56px;object-fit:cover;border-radius:8px;" />',
                obj.image.url
            )
        return "-"


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("id", "image_preview", "name", "date_up")
    search_fields = ("name", "content")
    ordering = ("-id",)
    list_per_page = 25

    @admin.display(description="Image")
    def image_preview(self, obj: Article):
        if obj.image:
            return format_html(
                '<img src="{}" style="width:56px;height:56px;object-fit:cover;border-radius:8px;" />',
                obj.image.url
            )
        return "-"


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "complete", "date_order", "item_count", "order_total_vnd", "transaction_id")
    list_filter = ("complete", "date_order")
    search_fields = ("id", "customer__name", "customer__email", "customer__user__username", "transaction_id")
    date_hierarchy = "date_order"
    ordering = ("-date_order",)
    inlines = [OrderItemInline, ShippingAddressInline]
    actions = [mark_complete, mark_incomplete, merge_duplicate_items]
    list_per_page = 25

    @admin.display(description="Items")
    def item_count(self, obj: Order):
        try:
            return obj.get_cart_items
        except Exception:
            return 0

    @admin.display(description="Total (VNĐ)")
    def order_total_vnd(self, obj: Order):
        try:
            return f"{int(obj.get_cart_total):,}"
        except Exception:
            return "0"


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "product", "quantity", "line_total_vnd", "date_added")
    search_fields = ("order__id", "product__name", "product__code")
    list_filter = ("date_added",)
    autocomplete_fields = ("order", "product")
    ordering = ("-date_added",)
    list_per_page = 50

    @admin.display(description="Line total (VNĐ)")
    def line_total_vnd(self, obj: OrderItem):
        try:
            return f"{int(obj.get_total):,}"
        except Exception:
            return "0"


@admin.register(ShippingAddress)
class ShippingAddressAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "customer", "address", "city", "state", "mobile", "date_added")
    search_fields = ("order__id", "customer__name", "address", "city", "state", "mobile")
    list_filter = ("date_added",)
    autocomplete_fields = ("order", "customer")
    ordering = ("-date_added",)
    list_per_page = 50
