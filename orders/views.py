import datetime
from email.message import EmailMessage
import json
from django.shortcuts import redirect, render
from carts.models import CartItem
from orders.forms import OrderForm
from orders.models import Order, OrderProduct, Payment
from store.models import Product
from django.template.loader import render_to_string
from django.core.mail import EmailMessage
from django.http import JsonResponse

def payments(request):
    body = json.loads(request.body)
    order = Order.objects.get(order_number=body['orderID'])    # store transaction details in order model
    payment = Payment(
        user=request.user,
        payment_id=body['transID'],
        payment_method=body['payment_method'],
        amount_paid=order.order_total,
        status=body['status'],
        
    )
    payment.save()
    
    order.payment = payment
    order.is_ordered = True
    order.save()
    
    # move to the cart items to order product table
    cart_items = CartItem.objects.filter(user=request.user)
    for item in cart_items:
        order_product = OrderProduct()
        order_product.order_id = order.id
        order_product.payment = payment
        order_product.user_id = request.user.id
        order_product.product_id = item.product_id
        order_product.quantity = item.quantity
        order_product.product_price = item.product.price
        order_product.ordered = True
        order_product.save()
        
        
        cart_items = CartItem.objects.filter(user=request.user) # clear the cart after order is placed
        product_variation =item.variations.all()
        orderproduct = OrderProduct.objects.get(id=order_product.id)
        orderproduct.variations.set(product_variation)
        orderproduct.save()

    #  reduce the quantity of sold products
    product = Product.objects.get(id=item.product_id)
    product.stock -= item.quantity
    product.save()
    
    # clear the cart
    CartItem.objects.filter(user=request.user).delete()
    
    # send order received email to customer
    mail_subject = 'Thank you for your order!'
    message = render_to_string('orders/order_received_email.html', {
        'user': request.user,
        'order': order,
      
    })
        
    to_email = request.user.email
    send_email = EmailMessage(mail_subject, message, to=[to_email])
    send_email.send()
    
    # send order number and transaction id back to sendData method via json response
    data = {
        'order_number': order.order_number,
        'transID': payment.payment_id,
    }
    return JsonResponse({
    'redirect_url': '/orders/order_complete/?order_number='+order.order_number+'&payment_id='+payment.payment_id
})
    
    


def place_order(request, total=0, quantity=0):
    current_user = request.user
    
    # If the cart is empty, redirect to store
    cart_items = CartItem.objects.filter(user=current_user)
    cart_count = cart_items.count()
    if cart_count <= 0:
        return redirect('store')
    
    # Calculate total and quantity correctly
    total = 0
    quantity = 0
    for cart_item in cart_items:
        total += (cart_item.product.price * cart_item.quantity)
        quantity += cart_item.quantity

    tax = (2 * total) / 100
    grand_total = total + tax

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            # Save order
            data = Order()
            data.user = current_user
            data.first_name = form.cleaned_data['first_name']
            data.last_name = form.cleaned_data['last_name']
            data.phone = form.cleaned_data['phone']
            data.email = form.cleaned_data['email']
            data.address_line_1 = form.cleaned_data['address_line_1']
            data.address_line_2 = form.cleaned_data['address_line_2']
            data.country = form.cleaned_data['country']
            data.state = form.cleaned_data['state']
            data.city = form.cleaned_data['city']
            data.order_note = form.cleaned_data['order_note']  # important!
            data.order_total = grand_total
            data.tax = tax
            data.ip = request.META.get('REMOTE_ADDR')

            data.save()

            # Generate order number
            yr = int(datetime.date.today().strftime('%Y'))
            dt = int(datetime.date.today().strftime('%d'))
            mt = int(datetime.date.today().strftime('%m'))
            d = datetime.date(yr, mt, dt)
            current_date = d.strftime("%Y%m%d")  # e.g., 20260312
            order_number = current_date + str(data.id)
            data.order_number = order_number
            data.save()

            # Pass the newly created order object to template
            context = {
                'order': data,       # ✅ fixed: use the saved object
                'cart_items': cart_items,
                'total': total,
                'tax': tax,
                'grand_total': grand_total,
            }

            return render(request, 'orders/payments.html', context)
        else:
            return redirect('checkout')

    return redirect('checkout')



def order_complete(request):
    order_number = request.GET.get('order_number')
    transID = request.GET.get('payment_id')
    
    try:
        order = Order.objects.get(order_number=order_number, is_ordered=True)
        ordered_products = OrderProduct.objects.filter(order_id=order.id)
        
        subtotal=0
        for i in ordered_products:
            subtotal = i.product_price * i.quantity
        payment = Payment.objects.get(payment_id=transID)
        context = {
            'order': order,
            'ordered_products': ordered_products,
            'order_number': order.order_number,
            'transID': transID,
            'payment': payment,
            'subtotal': subtotal,
        }
    
        return render(request, 'orders/order_complete.html', context)
    
    
    except (Order.DoesNotExist, Payment.DoesNotExist):
        return redirect('home')