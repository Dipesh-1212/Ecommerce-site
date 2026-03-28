from email import message
from pyexpat.errors import messages

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Q
from carts.models import CartItem
from carts.views import _cart_id
from category.models import Category
from orders.models import OrderProduct
from store.forms import ReviewForm
from .models import Product, ProductGallery, ReviewRating, Variation
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.contrib import messages
# Create your views here.

def store(request, category_slug = None):
    categories = None
    products = None
    if category_slug != None:
        categories = get_object_or_404(Category, slug = category_slug)
        products = Product.objects.all().filter(is_available = True )
        paginator = Paginator(products,1)
        page = request.GET.get('page')
        paged_products = paginator.get_page(page)        
        
        products = Product.objects.filter(category = categories, is_available = True)
        products_count = products.count()
    else:
        
        products = Product.objects.all().filter(is_available = True ).order_by('id')
        paginator = Paginator(products,3)
        page = request.GET.get('page')
        paged_products = paginator.get_page(page)
        products_count = products.count()
        categories = Category.objects.all()
    context = {
        'products':paged_products,
        'products_count':products_count,    
        'categories':categories,
    }
    return render(request,"store/store.html",context)





def product_detail(request, category_slug, product_slug):

    # ✅ Get product (better filtering with category)
    single_product = get_object_or_404(
        Product,
        category__slug=category_slug,
        slug=product_slug
    )

    # ✅ Get variations
    colors = Variation.objects.filter(
        product=single_product,
        variation_category='color',
        is_active=True
    )

    sizes = Variation.objects.filter(
        product=single_product,
        variation_category='size',
        is_active=True
    )

    # ✅ Get reviews
    reviews = ReviewRating.objects.filter(
        product_id=single_product.id,
        status=True
    )

    # ✅ Check if user purchased product (IMPORTANT)
    if request.user.is_authenticated:
        orderproduct = OrderProduct.objects.filter(
            user=request.user,
            product_id=single_product.id,
            ordered=True
        ).exists()
    else:
        orderproduct = False

    product_gallery = ProductGallery.objects.filter(product_id=single_product.id)
    context = {
        'single_product': single_product,
        'reviews': reviews,
        'colors': colors,
        'sizes': sizes,
        'orderproduct': orderproduct,
        'product_gallery': product_gallery, 
    }

    return render(request, 'store/product_detail.html', context)

def search(request):
    if 'keyword' in request.GET:
        keyword = request.GET['keyword']
        if keyword:
            products = Product.objects.order_by('-created_date').filter(Q(description__icontains = keyword) | Q(product_name__icontains = keyword) )
            products_count = products.count()

    context = {
        'products':products,
        'products_count':products_count,
    }
    return render(request,"store/store.html", context)



def submit_review(request, product_id):
    url = request.META.get('HTTP_REFERER')

    if request.method == 'POST':
        try:
            # check if review already exists
            reviews = ReviewRating.objects.get(
                user__id=request.user.id,
                product__id=product_id
            )

            form = ReviewForm(request.POST, instance=reviews)

            if form.is_valid():
                form.save()
                messages.success(request, 'Your review has been updated.')

            return redirect(url)

        except ReviewRating.DoesNotExist:

            form = ReviewForm(request.POST)

            if form.is_valid():
                data = form.save(commit=False)
                data.product_id = product_id
                data.user_id = request.user.id
                data.ip = request.META.get('REMOTE_ADDR')
                data.save()

                messages.success(request, 'Your review has been submitted.')

            return redirect(url)

    return redirect(url)