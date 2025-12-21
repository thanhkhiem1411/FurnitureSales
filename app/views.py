from django.shortcuts import redirect, render, get_object_or_404
from django.http import JsonResponse, HttpResponseRedirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q, Count, Sum, Min
from django.views.decorators.http import require_POST
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
import json
import logging

from .models import *
from .forms import ProductForm, ArticleForm, DeliveryForm

logger = logging.getLogger(__name__)


# -----------------------------
# Helpers
# -----------------------------
def _is_admin(request) -> bool:
    return bool(request.session.get("admin", False))


def _get_order_context(request):
    """
    Return: (customer, order, items, cartItems)
    - Nếu anonymous hoặc admin -> trả order dummy, items empty
    """
    if request.user.is_authenticated and not _is_admin(request) and hasattr(request.user, "customer"):
        customer = request.user.customer
        order, _ = Order.objects.get_or_create(customer=customer, complete=False)
        items = order.orderitem_set.all()
        cartItems = order.get_cart_items
        return customer, order, items, cartItems

    # anonymous hoặc admin (hoặc user không có customer)
    customer = None
    order = {'get_cart_items': 0, 'get_cart_total': 0}
    items = []
    cartItems = 0
    return customer, order, items, cartItems


def _merge_duplicate_orderitems(order):
    """
    Fix lỗi bị duplicate OrderItem (cùng order + cùng product) do add nhiều request nhanh.
    Gộp chúng lại thành 1 row: quantity = tổng quantity, xoá các row dư.
    """
    if not order or isinstance(order, dict):
        return

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

        # update row giữ lại
        OrderItem.objects.filter(id=keep_id).update(quantity=total_qty)

        # xoá các row còn lại
        OrderItem.objects.filter(order=order, product_id=g["product_id"]).exclude(id=keep_id).delete()


# -----------------------------
# Views
# -----------------------------
def home(request):
    is_admin = _is_admin(request)
    customer, order, items, cartItems = _get_order_context(request)

    articles = Article.objects.all()
    products = Product.objects.all()

    context = {
        "items": items,
        "order": order,
        "articles": articles,
        "products": products,
        "cartItems": cartItems,
        "is_admin": is_admin,
    }
    return render(request, "app/home.html", context)


def product(request):
    is_admin = _is_admin(request)
    customer, order, items, cartItems = _get_order_context(request)

    products = Product.objects.all()
    context = {
        "products": products,
        "cartItems": cartItems,
        "is_admin": is_admin,
    }
    return render(request, "app/product.html", context)


def product_detail(request, pk):
    product = get_object_or_404(Product, id=pk)

    is_admin = _is_admin(request)
    customer, order, items, cartItems = _get_order_context(request)

    context = {
        "product": product,
        "cartItems": cartItems,
        "is_admin": is_admin,
    }
    return render(request, "app/detail.html", context)


def article(request):
    is_admin = _is_admin(request)
    customer, order, items, cartItems = _get_order_context(request)

    articles = Article.objects.all()
    context = {
        "articles": articles,
        "cartItems": cartItems,
        "is_admin": is_admin,
    }
    return render(request, "app/article.html", context)


def cart(request):
    is_admin = _is_admin(request)
    customer, order, items, cartItems = _get_order_context(request)

    # ✅ Gộp duplicate để cart hiển thị đúng
    if request.user.is_authenticated and not is_admin and not isinstance(order, dict):
        _merge_duplicate_orderitems(order)
        items = order.orderitem_set.all()
        cartItems = order.get_cart_items

    context = {
        "items": items,
        "order": order,
        "cartItems": cartItems,
        "is_admin": is_admin,
    }
    return render(request, "app/cart.html", context)


@require_POST
def updateItem(request):
    """
    AJAX add/remove item.
    ✅ Fix duplicate OrderItem khi user add nhiều lần nhanh bằng:
      - transaction.atomic
      - merge duplicates sau mỗi lần update
    """
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "error": "Please login first."}, status=401)

    if _is_admin(request):
        return JsonResponse({"ok": False, "error": "Admin account cannot add to cart here."}, status=403)

    if not hasattr(request.user, "customer"):
        return JsonResponse({"ok": False, "error": "Customer profile not found."}, status=400)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        data = {}

    productId = data.get("productId")
    action = data.get("action", "add")

    if not productId:
        return JsonResponse({"ok": False, "error": "Missing productId."}, status=400)

    customer = request.user.customer
    product = get_object_or_404(Product, id=productId)

    with transaction.atomic():
        order, _ = Order.objects.get_or_create(customer=customer, complete=False)

        # merge trước (phòng trường hợp đã bị duplicate từ trước)
        _merge_duplicate_orderitems(order)

        orderItem, created = OrderItem.objects.get_or_create(order=order, product=product)

        if action == "add":
            orderItem.quantity += 1
            orderItem.save()

        elif action == "remove":
            orderItem.quantity -= 1
            if orderItem.quantity <= 0:
                orderItem.delete()
            else:
                orderItem.save()

        else:
            return JsonResponse({"ok": False, "error": "Invalid action."}, status=400)

        # merge lại lần nữa để chắc chắn không còn duplicate
        _merge_duplicate_orderitems(order)

    return JsonResponse({"ok": True})


def checkout(request):
    is_admin = _is_admin(request)

    if request.user.is_authenticated and not is_admin and hasattr(request.user, "customer"):
        customer = request.user.customer
        order, _ = Order.objects.get_or_create(customer=customer, complete=False)

        # ✅ gộp duplicate để tổng tiền đúng
        _merge_duplicate_orderitems(order)

        items = order.orderitem_set.all()
        cartItems = order.get_cart_items

        discount_amount = int(request.session.get("discount_amount", 0) or 0)
        discount_code = request.session.get("discount_code", "")

        subtotal = int(order.get_cart_total)
        if discount_amount > subtotal:
            discount_amount = subtotal
            request.session["discount_amount"] = discount_amount

        final_total = subtotal - discount_amount

    else:
        items = []
        order = {'get_cart_items': 0, 'get_cart_total': 0}
        cartItems = 0
        discount_amount = 0
        discount_code = ""
        final_total = 0

    context = {
        "items": items,
        "order": order,
        "cartItems": cartItems,
        "discount_amount": discount_amount,
        "discount_code": discount_code,
        "final_total": final_total,
        "is_admin": is_admin,
    }
    return render(request, "app/checkout.html", context)


@require_POST
def apply_discount(request):
    """
    ✅ Apply discount bằng AJAX (không redirect).
    Lưu discount vào session để checkout hiển thị.
    """
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "error": "Please login first."}, status=401)

    if _is_admin(request):
        return JsonResponse({"ok": False, "error": "Admin account cannot apply discount here."}, status=403)

    if not hasattr(request.user, "customer"):
        return JsonResponse({"ok": False, "error": "Customer profile not found."}, status=400)

    try:
        data = json.loads(request.body.decode("utf-8"))
    except Exception:
        data = {}

    code = (data.get("code") or "").strip().upper()

    customer = request.user.customer
    order, _ = Order.objects.get_or_create(customer=customer, complete=False)

    _merge_duplicate_orderitems(order)

    subtotal = int(order.get_cart_total)

    # ✅ Bạn sửa danh sách mã tại đây (file chứa mã giảm giá chính là views.py)
    COUPONS = {
        "SAVE10": {"type": "percent", "value": 10},      # giảm 10%
        "SAVE5": {"type": "percent", "value": 5},        # giảm 5%
        "LESS100K": {"type": "fixed", "value": 100000},  # giảm 100k
    }

    if not code or code not in COUPONS:
        request.session["discount_code"] = ""
        request.session["discount_amount"] = 0
        return JsonResponse({
            "ok": False,
            "error": "Invalid discount code.",
            "subtotal": subtotal,
            "discount": 0,
            "total": subtotal,
        })

    rule = COUPONS[code]
    if rule["type"] == "percent":
        discount = round(subtotal * rule["value"] / 100)
    else:
        discount = min(int(rule["value"]), subtotal)

    total = subtotal - int(discount)

    request.session["discount_code"] = code
    request.session["discount_amount"] = int(discount)

    return JsonResponse({
        "ok": True,
        "code": code,
        "subtotal": subtotal,
        "discount": int(discount),
        "total": total,
    })


def payPage(request):
    """
    ✅ Sau khi thanh toán xong:
    - Không crash vì lỗi SSL gửi mail
    - Redirect sang trang success đẹp hơn
    """
    submitted = False

    if request.user.is_authenticated and not _is_admin(request) and hasattr(request.user, "customer"):
        customer = request.user.customer
        order, _ = Order.objects.get_or_create(customer=customer, complete=False)

        _merge_duplicate_orderitems(order)

        # giỏ trống thì quay về product
        if order.get_cart_items == 0:
            messages.info(request, "Your cart is empty.")
            return redirect("product")

        form = DeliveryForm(initial={'customer': customer, 'order': order})

        if request.method == 'POST':
            form = DeliveryForm(request.POST)
            if form.is_valid():
                delivery = form.save(commit=False)
                delivery.customer = customer
                delivery.order = order
                delivery.save()

                # Tính tổng + discount (để show ở success page / email)
                subtotal = int(order.get_cart_total)
                discount_amount = int(request.session.get("discount_amount", 0) or 0)
                if discount_amount > subtotal:
                    discount_amount = subtotal
                final_total = subtotal - discount_amount
                discount_code = request.session.get("discount_code", "")

                # Complete order
                order.complete = True
                order.save()

                # Lưu summary vào session để trang success hiển thị
                request.session["last_order_id"] = order.id
                request.session["last_subtotal"] = subtotal
                request.session["last_discount_amount"] = discount_amount
                request.session["last_discount_code"] = discount_code
                request.session["last_final_total"] = final_total

                # ✅ Clear discount sau khi thanh toán (cho order tiếp theo)
                request.session["discount_code"] = ""
                request.session["discount_amount"] = 0

                # Email nội dung (bọc try/except để không crash vì SSL)
                try:
                    order_items = order.orderitem_set.all()
                    order_details = "\n".join([
                        f"{item.product.name}: {item.quantity} x {item.product.price} VNĐ"
                        for item in order_items
                    ])

                    message = f"""
Hi {customer.name}, You have successfully placed an order at HomeClick!

Order Details:
{order_details}

Subtotal: {subtotal} VNĐ
Discount ({discount_code if discount_code else "N/A"}): -{discount_amount} VNĐ
Total after discount: {final_total} VNĐ

We hope you enjoy our service!
"""
                    sendMail("Order confirmed successfully.", message, customer.email)
                except Exception as e:
                    logger.warning("Send mail failed (ignored): %s", e)

                # ✅ Redirect sang trang success đẹp hơn
                return redirect("payment_success", order_id=order.id)

    else:
        form = DeliveryForm()
        if 'submitted' in request.GET:
            submitted = True

    context = {'form': form, 'submitted': submitted, "is_admin": _is_admin(request)}
    return render(request, "app/paypage.html", context)


@login_required
def payment_success(request, order_id):
    """
    Trang thanh toán thành công (bạn tạo template: app/payment_success.html)
    """
    if _is_admin(request) or (not hasattr(request.user, "customer")):
        return redirect("home")

    customer = request.user.customer
    paid_order = get_object_or_404(Order, id=order_id, customer=customer)

    paid_items = paid_order.orderitem_set.select_related("product").all()

    # lấy summary từ session (nếu có)
    last_order_id = request.session.get("last_order_id")
    subtotal = request.session.get("last_subtotal", None)
    discount_amount = request.session.get("last_discount_amount", 0)
    discount_code = request.session.get("last_discount_code", "")
    final_total = request.session.get("last_final_total", None)

    # chỉ dùng session nếu đúng order vừa thanh toán
    if last_order_id != paid_order.id:
        subtotal = int(paid_order.get_cart_total)
        discount_amount = 0
        discount_code = ""
        final_total = subtotal

    # (tuỳ bạn) clear session summary sau khi hiển thị 1 lần
    request.session.pop("last_order_id", None)
    request.session.pop("last_subtotal", None)
    request.session.pop("last_discount_amount", None)
    request.session.pop("last_discount_code", None)
    request.session.pop("last_final_total", None)

    context = {
        "is_admin": _is_admin(request),
        "paid_order": paid_order,
        "paid_items": paid_items,
        "subtotal": subtotal,
        "discount_amount": discount_amount,
        "discount_code": discount_code,
        "final_total": final_total,
    }
    return render(request, "app/payment_success.html", context)


@login_required
def profileUser(request):
    user = request.user
    customer = Customer.objects.get(user=user)

    if request.method == 'POST':
        phone_number = request.POST.get('phone_number')
        address = request.POST.get('address')

        if phone_number:
            customer.phone_number = phone_number
        if address:
            customer.address = address
        customer.save()

        return JsonResponse({'status': 'success'})

    context = {
        'user': user,
        'phone_number': customer.phone_number,
        'address': customer.address,
        "is_admin": _is_admin(request),
    }
    return render(request, 'app/profile.html', context)


def detail(request):
    # Backward compatibility nếu bạn còn link name='detail'
    return redirect("product")


def signup(request):
    if request.method == "POST":
        username = request.POST.get('username', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if password != confirm_password:
            messages.error(request, "Password doesn't match. Please try again.")
            return redirect('signup')

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        customer = Customer.objects.create(user=user, name=user.username, email=user.email)
        user.save()
        customer.save()

        messages.success(request, 'You have successfully registered! Please log in to continue.')
        return render(request, "app/login.html")

    return render(request, "app/register.html")


def signin(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == "POST":
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(username=username, password=password)

        if user is not None:
            login(request, user)

            # nếu không có customer => coi như admin
            if not hasattr(request.user, 'customer'):
                request.session['admin'] = True
            else:
                request.session['admin'] = False

            return redirect('home')
        else:
            messages.info(request, 'Username or password is not correct!!!')

    return render(request, "app/login.html")


def custom_logout(request):
    logout(request)
    messages.success(request, 'You have successfully logged out!')
    return redirect('home')


# Admin role
def addArticle(request):
    submitted = False
    if request.method == 'POST':
        form = ArticleForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect('/addArticle?submitted=True')
    else:
        form = ArticleForm
        if 'submitted' in request.GET:
            submitted = True

    context = {'form_A': form, 'submitted': submitted, "is_admin": _is_admin(request)}
    return render(request, 'app/addArticle.html', context)


def addProduct(request):
    submitted = False
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect('/addProduct?submitted=True')
    else:
        form = ProductForm
        if 'submitted' in request.GET:
            submitted = True

    context = {'form': form, 'submitted': submitted, "is_admin": _is_admin(request)}
    return render(request, 'app/addproduct.html', context)


def searchpage(request):
    customer, order, items, cartItems = _get_order_context(request)

    if request.method == "POST":
        searched = request.POST.get('searched', '').strip()
        product = Product.objects.filter(Q(name__icontains=searched) | Q(code__icontains=searched))
        return render(request, "app/searchpage.html", {
            'searched': searched,
            'product': product,
            'cartItems': cartItems,
            'is_admin': _is_admin(request),
        })

    return render(request, "app/searchpage.html", {
        'cartItems': cartItems,
        'is_admin': _is_admin(request),
    })


def sendMail(subject, message, receiver):
    """
    ✅ Fix lỗi SSL CERTIFICATE_VERIFY_FAILED:
    nếu gửi mail lỗi thì không làm crash thanh toán.
    """
    try:
        sender = settings.EMAIL_HOST_USER
        send_mail(
            subject,
            message,
            sender,
            [receiver],
            fail_silently=False,
        )
    except Exception as e:
        logger.warning("sendMail failed (ignored): %s", e)


