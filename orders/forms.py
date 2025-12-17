from django import forms
from .models import Order

class OrderCreateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['first_name', 'last_name', 'email', 'address',
                  'postal_code', 'city']
        widgets = {
            'email': forms.EmailInput(attrs={'placeholder': 'seu@email.com'}),
            'address': forms.TextInput(attrs={'placeholder': 'Rua, número, bairro'}),
        }