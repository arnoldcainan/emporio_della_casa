from django import forms

class CourseEnrollmentForm(forms.Form):
    full_name = forms.CharField(label="Nome Completo", max_length=100)
    cpf = forms.CharField(label="CPF", max_length=14)
    phone = forms.CharField(label="WhatsApp/Telefone", max_length=15)