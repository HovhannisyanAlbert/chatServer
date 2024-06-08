from django.db import models
from django.contrib.auth.models import User


class User(models.Model):

    user_name = models.CharField(max_length=150, unique=True)
    user_image = models.ImageField(
        upload_to='user_image', null=True, blank=True, default="default.png")

    def __str__(self):
        return self.user_name


class Room(models.Model):
    name = models.CharField(max_length=100)
    members = models.ManyToManyField(User)

    def __str__(self):
        return self.name


class Message(models.Model):
    room = models.ForeignKey(
        Room,  on_delete=models.CASCADE)
    user = models.ForeignKey(
        User,  on_delete=models.CASCADE)
    message = models.TextField(max_length=900)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.user_name} - {self.timestamp}"
