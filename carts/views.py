from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render

from carts.models import Cart, CartItem
from store.models import Product, Variation
from django.core.exceptions import ObjectDoesNotExist

# Create your views here.
def _cart_id(request):
    cart = request.session.session_key
    if not cart:
        cart = request.session.create()
    return cart
    

def add_cart(request, product_id):
    product = Product.objects.get(id=product_id)
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
            except Variation.DoesNotExist:
                pass

    # Get or create cart
    try:
        cart = Cart.objects.get(cart_id=_cart_id(request))
    except Cart.DoesNotExist:
        cart = Cart.objects.create(cart_id=_cart_id(request))

    # Get cart items for this product
    cart_items = CartItem.objects.filter(product=product, cart=cart)

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
        cart_item = CartItem.objects.create(
            product=product,
            quantity=1,
            cart=cart
        )

        if len(product_variation) > 0:
            cart_item.variations.add(*product_variation)

        cart_item.save()

    return redirect('cart')


def remove_cart(request, cart_item_id):
    
    cart = Cart.objects.get(cart_id=_cart_id(request))

    try:
        cart_item = CartItem.objects.get(id=cart_item_id, cart=cart)

        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        else:
            cart_item.delete()

    except CartItem.DoesNotExist:
        pass

    return redirect('cart')


def remove_cart_item(request, product_id):
    cart = Cart.objects.get(cart_id = _cart_id(request))
    product = get_object_or_404(Product, id = product_id)
    cart_item = CartItem.objects.get(product = product, cart = cart)
    cart_item.delete()
    return redirect ('cart')
        
        
        
def cart(request, total = 0, quantity = 0, cart_items = None):
    try:
        cart = Cart.objects.get(cart_id = _cart_id(request))
        cart_items = CartItem.objects.filter(cart =cart, is_active = True)
        for cart_item in cart_items:
            total += (cart_item.product.price * cart_item.quantity)
            quantity += cart_item.quantity
        tax = (2 * total)/100
        
        grand_total = total + tax
            
    except ObjectDoesNotExists:
        pass
    
    
    
    context = {
        'total': total,
        'quantity':quantity,
        'cart_items':cart_items,
        'tax': tax,
        'grand_total': grand_total, 
    }
    return render(request, 'store/cart.html',context)