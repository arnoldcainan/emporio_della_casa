from django.db import models

class Newsletter(models.Model):
    email = models.EmailField(unique=True, error_messages={
        'unique': "Este e-mail já está cadastrado."
    })
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email