from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from carts.models import Cart, CartItem
from store.models import Product, Variation


# =========================
# SESSION CART ID
# =========================
def _cart_id(request):
    cart = request.session.session_key
    if not cart:
        cart = request.session.create()
    return cart


# =========================
# ADD TO CART
# =========================
def add_cart(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product_variation = []

    if request.method == "POST":
        for key in request.POST:
            value = request.POST[key]
            try:
                variation = Variation.objects.get(
                    product=product,
                    variation_category__iexact=key,
                    variation_value__iexact=value
                )
                product_variation.append(variation)
            except:
                pass

    if request.user.is_authenticated:
        # Logged in user cart
        cart_items = CartItem.objects.filter(
            product=product,
            user=request.user
        )
    else:
        # Guest cart
        cart, created = Cart.objects.get_or_create(
            cart_id=_cart_id(request)
        )
        cart_items = CartItem.objects.filter(
            product=product,
            cart=cart
        )

    # Check existing variations
    existing_variations_list = []
    cart_item_ids = []

    for item in cart_items:
        existing_variations = list(item.variations.all())
        existing_variations_list.append(existing_variations)
        cart_item_ids.append(item.id)

    if product_variation in existing_variations_list:
        index = existing_variations_list.index(product_variation)
        cart_item = CartItem.objects.get(id=cart_item_ids[index])
        cart_item.quantity += 1
        cart_item.save()
    else:
        if request.user.is_authenticated:
            cart_item = CartItem.objects.create(
                product=product,
                quantity=1,
                user=request.user
            )
        else:
            cart_item = CartItem.objects.create(
                product=product,
                quantity=1,
                cart=cart
            )

        if len(product_variation) > 0:
            cart_item.variations.add(*product_variation)

        cart_item.save()

    return redirect('cart')


# =========================
# REMOVE SINGLE QUANTITY
# =========================
def remove_cart(request, cart_item_id):
    try:
        if request.user.is_authenticated:
            cart_item = CartItem.objects.get(
                id=cart_item_id,
                user=request.user
            )
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_item = CartItem.objects.get(
                id=cart_item_id,
                cart=cart
            )

        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()

    except:
        pass

    return redirect('cart')


# =========================
# REMOVE ENTIRE ITEM
# =========================
def remove_cart_item(request, cart_item_id):
    try:
        if request.user.is_authenticated:
            cart_item = CartItem.objects.get(
                id=cart_item_id,
                user=request.user
            )
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_item = CartItem.objects.get(
                id=cart_item_id,
                cart=cart
            )

        cart_item.delete()

    except:
        pass

    return redirect('cart')


# =========================
# CART PAGE
# =========================
def cart(request):
    total = 0
    quantity = 0
    tax = 0
    grand_total = 0
    cart_items = []

    try:
        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(
                user=request.user,
                is_active=True
            )
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_items = CartItem.objects.filter(
                cart=cart,
                is_active=True
            )

        for cart_item in cart_items:
            total += cart_item.sub_total()
            quantity += cart_item.quantity

        tax = (2 * total) / 100
        grand_total = total + tax

    except ObjectDoesNotExist:
        pass

    context = {
        'total': total,
        'quantity': quantity,
        'cart_items': cart_items,
        'tax': tax,
        'grand_total': grand_total,
    }

    return render(request, 'store/cart.html', context)


# =========================
# CHECKOUT
# =========================
@login_required(login_url='login')
def checkout(request):
    total = 0
    quantity = 0
    tax = 0
    grand_total = 0

    cart_items = CartItem.objects.filter(
        user=request.user,
        is_active=True
    )

    for cart_item in cart_items:
        total += cart_item.sub_total()
        quantity += cart_item.quantity

    tax = (2 * total) / 100
    grand_total = total + tax

    context = {
        'total': total,
        'quantity': quantity,
        'cart_items': cart_items,
        'tax': tax,
        'grand_total': grand_total,
    }

    return render(request, 'store/checkout.html', context)