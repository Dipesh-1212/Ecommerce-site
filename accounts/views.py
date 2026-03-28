from django.shortcuts import render, redirect
from django.contrib import messages, auth
from accounts.forms import RegistrationForm, UserProfileForm, UserForm
from accounts.models import Account
from django.contrib.sites.shortcuts import get_current_site
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage
from django.conf import settings  # Added: to access DEFAULT_FROM_EMAIL
import smtplib
import logging
import glob
import os
from pathlib import Path
from django.contrib import messages
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required

from carts.models import Cart, CartItem
from carts.views import _cart_id
from .models import UserProfile
from django.shortcuts import get_object_or_404




import requests

from orders.models import Order, OrderProduct, Payment







# ================= REGISTER =================

def register(request):

    if request.method == "POST":

        form = RegistrationForm(request.POST)

        if form.is_valid():

            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            phone_number = form.cleaned_data['phone_number']
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']

            username = email.split("@")[0]

            user = Account.objects.create_user(
                first_name=first_name,
                last_name=last_name,
                email=email,
                username=username,
                password=password
            )

            user.phone_number = phone_number
            user.is_active = True   # ✅ VERY IMPORTANT
            user.save()

            
            # User Activation
            current_site = get_current_site(request)
            mail_subject = "please activate your account"
            message = render_to_string('accounts/account_verification_email.html',{
                'user':user,
                'domain':current_site,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
                
                
            })
            to_email = email
            # Changed: include explicit from_email so SMTP provider (Gmail) accepts the sender
            send_email = EmailMessage(mail_subject, message, settings.DEFAULT_FROM_EMAIL, [to_email])
            try:
                send_email.send(fail_silently=False)
                # If using file-based backend in development, find the latest saved file and inform the developer
                if settings.EMAIL_BACKEND and 'filebased' in settings.EMAIL_BACKEND:
                    email_dir = getattr(settings, 'EMAIL_FILE_PATH', None)
                    if email_dir:
                        try:
                            files = glob.glob(os.path.join(email_dir, '*'))
                            if files:
                                latest = max(files, key=os.path.getctime)
                                messages.info(request, f"Activation email saved to: {latest}")
                        except Exception:
                            logging.exception("Failed to locate saved email file")
            except smtplib.SMTPAuthenticationError as e:
                logging.exception("SMTP authentication failed while sending activation email")
                messages.error(request, "Registration succeeded but the activation email could not be sent: authentication failed. Please check email credentials or use an App Password.")
            except Exception:
                logging.exception("Unexpected error while sending activation email")
                messages.error(request, "Registration succeeded but we couldn't send the activation email. Check server logs for details.")
            
            
            
            # messages.success(request, "Thank you for registring with us.👍 We have sent you a verification email to your email address. Please verify it.")

            return redirect(f'/accounts/login/?command=verification&email='+email )

    else:
        form = RegistrationForm()

    return render(request, 'accounts/register.html', {'form': form})

# ================= LOGIN =================






def login(request):

    # Clear old messages
    storage = messages.get_messages(request)
    for _ in storage:
        pass

    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')

        user = auth.authenticate(request, email=email, password=password)

        if user is not None:

            # 🔥 LOGIN FIRST
            auth.login(request, user)

            # 🔥 THEN MERGE CART
            try:
                cart = Cart.objects.get(cart_id=_cart_id(request))
                cart_items = CartItem.objects.filter(cart=cart)

                for item in cart_items:

                    # Check if same product already exists for user
                    existing_item = CartItem.objects.filter(
                        product=item.product,
                        user=user
                    ).first()

                    if existing_item:
                        existing_item.quantity += item.quantity
                        existing_item.save()
                        item.delete()
                    else:
                        item.user = user
                        item.cart = None   # 🔥 VERY IMPORTANT
                        item.save()

            except Cart.DoesNotExist:
                pass

            messages.success(request, "You are logged in successfully 🎉")
            url = request.META.get('HTTP_REFERER')
            try:
                query = requests.utils.urlparse(url).query
                params = dict(x.split('=') for x in query.split('&'))
                if 'next' in params:
                    return redirect(params['next'])
                
                
            except:
                
                return redirect('dashboard')

        else:
            messages.error(request, "Invalid login credentials ❌")

    return render(request, 'accounts/login.html')
# ================= LOGOUT =================
@login_required(login_url='login')
def logout(request):

    auth.logout(request)

    messages.success(request, "You are logged out 👋")

    return redirect('login')



def activate(request, uidb64, token):
    
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = Account.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save()
        messages.success(request, "Your account has been activated successfully!")
        return redirect('login')
    else:
        messages.error(request, "Activation link is invalid or has expired.")
        return redirect('register')
    
    
    
# ================= DASHBOARD =================


@login_required(login_url='login')
def dashboard(request):
    
    orders = Order.objects.order_by('-created_at').filter(user_id=request.user.id, is_ordered=True)
    orders_count = orders.count()
    userprofile, created = UserProfile.objects.get_or_create(user=request.user)
    context = {
        'orders': orders,
        'orders_count': orders_count,
        'userprofile': userprofile,
    }
    return render(request, 'accounts/dashboard.html', context)



def forgotPassword(request):
    
    if request.method == "POST":
        email = request.POST.get('email')

        if Account.objects.filter(email=email).exists():
            user = Account.objects.get(email__exact=email)

            # User Activation
            current_site = get_current_site(request)
            mail_subject = "Reset Your Password"
            message = render_to_string('accounts/reset_password_email.html',{
                'user':user,
                'domain':current_site,
                'uid': urlsafe_base64_encode(force_bytes(user.pk)),
                'token': default_token_generator.make_token(user),
            })
            to_email = email
            send_email = EmailMessage(mail_subject, message, settings.DEFAULT_FROM_EMAIL, [to_email])
            try:
                send_email.send(fail_silently=False)
                messages.success(request, "Password reset email has been sent to your email address.")
            except smtplib.SMTPAuthenticationError as e:
                logging.exception("SMTP authentication failed while sending password reset email")
                messages.error(request, "We couldn't send the password reset email: authentication failed. Please check email credentials or use an App Password.")
            except Exception:
                logging.exception("Unexpected error while sending password reset email")
                messages.error(request, "We couldn't send the password reset email. Check server logs for details.")
        else:
            messages.error(request, "Account with this email does not exist.")
    return render(request, 'accounts/forgotPassword.html')


def my_orders(request):
    orders = Order.objects.filter(user=request.user, is_ordered=True).order_by('-created_at')
    userprofile = UserProfile.objects.get(user_id=request.user.id)
    context = {
        'orders': orders,
        'userprofile': userprofile,
    }
    return render(request, 'accounts/my_orders.html', context)





def resetpassword_validate(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = Account.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, Account.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        request.session['uid'] = uid  # store uid in session for resetPassword
        messages.success(request, "Please reset your password")
        return redirect('resetPassword')
    else:
        messages.error(request, "This link is invalid or has expired!")
        return redirect('forgotPassword')



def resetPassword(request):
    if request.method == "POST":
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect('resetPassword')

        uid = request.session.get('uid')
        if uid:
            try:
                user = Account.objects.get(pk=uid)
                user.set_password(password)
                user.save()
                messages.success(request, "Password reset successful. You can now login.")
                return redirect('login')
            except Account.DoesNotExist:
                messages.error(request, "Something went wrong. Try again.")
                return redirect('forgotPassword')
        else:
            messages.error(request, "Session expired. Please try again.")
            return redirect('forgotPassword')

    return render(request, 'accounts/resetPassword.html')




def edit_profile(request):

    userprofile, created = UserProfile.objects.get_or_create(user=request.user)

    if request.method == 'POST':
      
        user_form = UserForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=userprofile)

        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, "Your profile has been updated successfully.")
            return redirect('edit_profile')
        else:
            if user_form.errors:
                for field in user_form.errors:
                    messages.error(request, f"{field}: {user_form.errors[field]}")
            if profile_form.errors:
                for field in profile_form.errors:
                    messages.error(request, f"{field}: {profile_form.errors[field]}")
    else:
        user_form = UserForm(instance=request.user)
        profile_form = UserProfileForm(instance=userprofile)

    context = {
        'user_form': user_form,
        'user_profile_form': profile_form,
        'userprofile': userprofile,
    }

    return render(request, 'accounts/edit_profile.html', context)


from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash

@login_required(login_url='login')
def change_password(request):
    if request.method == 'POST':
        current_password = request.POST.get('current_password')
        new_password = request.POST.get('new_password')
        confirm_password = request.POST.get('confirm_password')

        if not current_password or not new_password or not confirm_password:
            messages.error(request, "All password fields are required.")
            return redirect('change_password')

        if not request.user.check_password(current_password):
            messages.error(request, "Current password is incorrect.")
            return redirect('change_password')

        if new_password != confirm_password:
            messages.error(request, "New passwords do not match.")
            return redirect('change_password')

        # 🔥 Change password
        request.user.set_password(new_password)
        request.user.save()

        # 🔥 Keep user logged in (optional but better UX)
        update_session_auth_hash(request, request.user)

        messages.success(request, "Password changed successfully ✅")
        return redirect('dashboard')

    return render(request, 'accounts/change_password.html')


@login_required(login_url='login')
def order_detail(request, order_id):
    
    # ✅ Safe order fetch
    order = get_object_or_404(Order, id=order_id, user=request.user, is_ordered=True)

    # ✅ Fix profile issue
    userprofile, created = UserProfile.objects.get_or_create(user=request.user)

    # ✅ Get ordered products
    ordered_products = OrderProduct.objects.filter(order=order)

    # ✅ Calculate subtotal
    subtotal = 0
    for i in ordered_products:
        subtotal += i.product_price * i.quantity

    # ✅ Get transaction ID
    try:
        payment = Payment.objects.get(order=order)
        transID = payment.payment_id
    except Payment.DoesNotExist:
        transID = "N/A"

    context = {
        'order': order,
        'userprofile': userprofile,
        'ordered_products': ordered_products,
        'subtotal': subtotal,
        'transID': transID,
    }

    return render(request, 'accounts/order_detail.html', context)