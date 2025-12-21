from django import forms
from django.forms import ModelForm
from .models import Product, Article, ShippingAddress

class ProductForm(ModelForm):
    class Meta:
        model = Product
        fields = "__all__"

        labels = {
            'name': 'Name of product',
            'price': 'Price of product',
            'code': 'Code of product',
            'digital': 'Number of product',
            'image': 'Image of product',
        }
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter name of product'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Enter price of product'}),
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter code of product'}),
            'digital': forms.Select(choices=[(True, 'Yes'), (False, 'No')], attrs={'class': 'form-control'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'placeholder': 'Choose image'}),
        }

class ArticleForm(ModelForm):
    class Meta:
        model = Article
        fields = "__all__"

        labels = {
            'name': 'Name of article',
            'image': 'Image of article',
            'date_up': 'Date up',
            'content': 'Content of article'
        }

        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Name of article'}),
            'image': forms.FileInput(attrs={'class': 'form-control', 'placeholder': 'Choose Image of article'}),
            'date_up': forms.DateInput(attrs={'class': 'form-control', 'placeholder': 'Enter Date up'}),
            'content': forms.Textarea(attrs={'class': 'form-control', 'placeholder': 'Enter content of article'}),
        }

class DeliveryForm(ModelForm):
    class Meta:
        model = ShippingAddress
        fields = "__all__"

        labels = {
            'customer': 'Name',
            'address': 'Address',
            'city': 'City',
            'state': 'Province/City',
            'mobile': 'Phone number',
        }
        widgets = {
            'order': forms.HiddenInput(),
            'customer': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Name'}),
            'address': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Address'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter City'}),
            'state': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Province/City'}),
            'mobile': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Phone number'}),
        }

    def __init__(self, *args, **kwargs):
        super(DeliveryForm, self).__init__(*args, **kwargs)
        print("Initializing DeliveryForm")
        if 'initial' in kwargs:
            initial = kwargs['initial']
            customer = initial.get('customer', None)
            if customer:
                self.fields['customer'].initial = str(customer.name)
                print("Customer: ", customer.name)
                self.fields['mobile'].initial = customer.phone_number
                self.fields['address'].initial = customer.address
            order = initial.get('order', None)
            if order:
                self.fields['order'].initial = order