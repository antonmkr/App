from django.db import models


class User(models.Model):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password_hash = models.CharField(max_length=256)
    password_salt = models.CharField(max_length=256)
    reset_token = models.CharField(max_length=256, blank=True, null=True)  # <-- Add this field
    created_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return self.username

class Client(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()

    def __str__(self):
        return self.name