from django import forms

class CourseEnrollmentForm(forms.Form):
    full_name = forms.CharField(
        label="Nome Completo",
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Seu nome completo'})
    )
    cpf = forms.CharField(
        label="CPF",
        max_length=14,
        widget=forms.TextInput(attrs={
            'class': 'form-control cpf-mask',
            'placeholder': '000.000.000-00'
        })
    )
    phone = forms.CharField(
        label="WhatsApp/Telefone",
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control phone-mask',
            'placeholder': '(00) 00000-0000'
        })
    )