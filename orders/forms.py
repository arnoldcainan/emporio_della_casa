from django import forms
from .models import Order
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm

class OrderCreateForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['first_name', 'last_name', 'email', 'phone', 'address', 'postal_code', 'city', 'state']

        widgets = {
            'email': forms.EmailInput(attrs={'placeholder': 'seu@email.com'}),
            'postal_code': forms.TextInput(attrs={
                'placeholder': '00000-000',
                'maxlength': '9',  # 8 números + 1 traço (se houver máscara)
                'class': 'form-control'
            }),
            'address': forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control bg-light'}),
            'city': forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control bg-light'}),
            'state': forms.TextInput(attrs={'readonly': 'readonly', 'class': 'form-control bg-light'}),

        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            return email.lower().strip()  # Converte para minúsculo e remove espaços extras
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        # Remove parênteses, espaços e traços para contar apenas os números
        digits_only = ''.join(filter(str.isdigit, phone))

        # Um número celular brasileiro com DDD deve ter exatamente 11 dígitos
        if len(digits_only) < 11:
            raise forms.ValidationError("O número de WhatsApp deve conter o DDD e mais 9 dígitos.")
        return phone


class CustomUserCreationForm(UserCreationForm):
    # Definimos o e-mail como campo obrigatório e proeminente
    email = forms.EmailField(required=True, label="E-mail")
    first_name = forms.CharField(required=True, label="Nome Completo")

    class Meta(UserCreationForm.Meta):
        model = User
        # Exibimos apenas Nome e E-mail (o username será o próprio e-mail)
        fields = ("first_name", "email",)

    def clean_email(self):
        email = self.cleaned_data.get('email').lower().strip()
        if User.objects.filter(username=email).exists():
            raise forms.ValidationError("Este e-mail já está cadastrado.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        email = self.cleaned_data["email"].lower().strip()
        user.email = email
        user.username = email  # Normalização: E-mail vira o Username
        if commit:
            user.save()
        return user