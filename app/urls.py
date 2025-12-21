"""
URL configuration for HomeFurniture project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from django.contrib.auth.views import LogoutView
from . import views

urlpatterns = [
    path('', views.home, name = "home"),
    path('product/',views.product, name="product"),
    path('checkout/',views.checkout, name="checkout"),
    path('payment-success/<int:order_id>/', views.payment_success, name='payment_success'),
    path("product/<int:pk>/", views.product_detail, name="product_detail"),
    path('apply-discount/', views.apply_discount, name='apply_discount'),
    path('update_item/', views.updateItem, name = 'update_item'),
    path('cart/',views.cart, name="cart"),
    path('detail/',views.detail, name="detail"),
    path("article/", views.article, name="article"),
    path('search_page/', views.searchpage, name='search_page'),
    path('signup/', views.signup, name='signup'),
    path('signin/', views.signin, name="signin"),
    path('proflie/', views.profileUser, name="profile"),
    path('logout/', views.custom_logout, name='logout'),
    path('pay_page/', views.payPage, name='pay_page'),
    path('addProduct/', views.addProduct, name='addProduct'),
    path('addArticle/', views.addArticle, name='addArticle'),
]
