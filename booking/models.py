from django.db import models
from django.contrib.auth.models import User



class Event(models.Model):
    name = models.CharField(max_length=200)
    date = models.DateTimeField()
    venue = models.CharField(max_length=200)

    total_seats = models.IntegerField()
    available_seats = models.IntegerField()

    price = models.IntegerField(default=50)

    # Extra details
    image = models.ImageField(upload_to='event_images/', null=True, blank=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.name



class Booking(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)

    seats_booked = models.IntegerField()
    selected_seats = models.CharField(max_length=200, null=True, blank=True)

    booking_time = models.DateTimeField(auto_now_add=True)

    # QR CODE
    qr_code = models.ImageField(upload_to='qr_codes/', null=True, blank=True)

    # PAYMENT
    payment_method = models.CharField(max_length=10, default='card')

    # TICKET STATUS
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username} - {self.event.name} ({self.selected_seats})"