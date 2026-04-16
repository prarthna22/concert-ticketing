from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .forms import CustomSignupForm, EventForm
from django.contrib.auth import login
from django.contrib import messages
from django.db.models import Q
from django.http import HttpResponse
from django.conf import settings
from django.core.mail import send_mail
import stripe

from .models import Event, Booking
from ticketing_utils.qr_generator import generate_qr
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum
import json
import os
from django.core.files import File

stripe.api_key = settings.STRIPE_SECRET_KEY

DOMAIN = "https://concert-ticketing.onrender.com"


@login_required
def event_list(request):
    query = request.GET.get('q')
    price_filter = request.GET.get('price')

    events = Event.objects.all()

    if query:
        events = events.filter(
            Q(name__icontains=query) |
            Q(venue__icontains=query)
        )

    if price_filter:
        events = events.filter(price__lte=price_filter)

    return render(request, 'booking/event_list.html', {
        'events': events,
        'query': query
    })


@login_required
def create_event(request):
    if not request.user.is_staff:
        return redirect('event_list')

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES)

        if form.is_valid():
            event = form.save(commit=False)
            event.total_seats = event.available_seats
            event.save()
            return redirect('event_list')

    else:
        form = EventForm()

    return render(request, 'booking/create_event.html', {'form': form})


@login_required
def edit_event(request, event_id):
    if not request.user.is_staff:
        return redirect('event_list')

    event = get_object_or_404(Event, id=event_id)

    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, instance=event)

        if form.is_valid():
            updated_event = form.save(commit=False)
            if not updated_event.total_seats:
                updated_event.total_seats = updated_event.available_seats
            updated_event.save()
            return redirect('event_list')

    else:
        form = EventForm(instance=event)

    return render(request, 'booking/edit_event.html', {
        'form': form,
        'event': event
    })


@login_required
def book_ticket(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    rows = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    seats = []

    total_seats = event.available_seats
    per_row = 10

    for i in range(total_seats):
        row_index = i // per_row
        row_letter = rows[row_index % len(rows)]
        number = (i % per_row) + 1
        seats.append(f"{row_letter}{number}")

    bookings = Booking.objects.filter(event=event)

    booked_seats = []
    for b in bookings:
        if b.selected_seats:
            booked_seats.extend(b.selected_seats.split(','))

    if request.method == "POST":
        seats_selected = request.POST.get('seats', '')
        seat_list = seats_selected.split(',') if seats_selected else []
        seat_count = len(seat_list)

        for seat in seat_list:
            if seat in booked_seats:
                messages.error(request, f"Seat {seat} already booked!")
                return redirect('book_ticket', event_id=event.id)

        if seat_count <= event.available_seats:
            total = seat_count * event.price

            return render(request, 'booking/payment.html', {
                'event': event,
                'seats': seats_selected,
                'seat_count': seat_count,
                'total': total
            })
        else:
            messages.error(request, "Not enough seats available!")

    return render(request, 'booking/book_ticket.html', {
        'event': event,
        'seats_list': seats,
        'booked_seats': booked_seats
    })


@login_required
def process_payment(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if request.method == "POST":
        seats = request.POST.get("seats", "")
        seat_list = seats.split(",") if seats else []
        seat_count = len(seat_list)

        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'eur',
                    'product_data': {
                        'name': event.name,
                    },
                    'unit_amount': int(event.price * 100),
                },
                'quantity': seat_count,
            }],
            mode='payment',
            success_url=f"{DOMAIN}/success/?event_id={event.id}&seats={seats}",
            cancel_url=f"{DOMAIN}/",
        )

        return redirect(checkout_session.url)

    return redirect('event_list')


@login_required
def success(request):
    try:
        event_id = request.GET.get("event_id")
        seats = request.GET.get("seats", "")

        event = get_object_or_404(Event, id=event_id)

        seat_list = seats.split(",") if seats else []
        seat_count = len(seat_list)

        booking = Booking.objects.create(
            user=request.user,
            event=event,
            seats_booked=seat_count,
            selected_seats=seats,
            payment_method="card"
        )

        # ✅ FIXED QR CODE SAVE
        qr_data = f"{DOMAIN}/use-ticket/{booking.id}/"
        filename = f"booking_{booking.id}.png"

        qr_path = generate_qr(qr_data, filename)

        if os.path.exists(qr_path):
            with open(qr_path, 'rb') as f:
                booking.qr_code.save(filename, File(f), save=True)

        event.available_seats -= seat_count
        event.save()

        return render(request, 'booking/success.html', {
            'booking': booking
        })

    except Exception as e:
        print("ERROR:", e)
        return HttpResponse("Something went wrong")


def download_ticket(request, booking_id):
    return HttpResponse(f"Download ticket for booking {booking_id}")


@login_required
def booking_history(request):
    bookings = Booking.objects.filter(user=request.user)

    return render(request, 'booking/history.html', {
        'bookings': bookings
    })


def signup(request):
    if request.method == "POST":
        form = CustomSignupForm(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('event_list')
    else:
        form = CustomSignupForm()

    return render(request, 'booking/signup.html', {
        'form': form
    })


@staff_member_required
def delete_event(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    if request.method == "POST":
        event.delete()
        return redirect('event_list')

    return render(request, 'booking/delete_event.html', {'event': event})


@staff_member_required
def dashboard(request):
    total_events = Event.objects.count()
    total_bookings = Booking.objects.count()

    total_tickets_sold = Booking.objects.aggregate(
        Sum('seats_booked')
    )['seats_booked__sum'] or 0

    total_revenue = sum(
        b.seats_booked * b.event.price
        for b in Booking.objects.all()
    )

    events = Event.objects.all()

    event_names = []
    booking_counts = []

    for event in events:
        event_names.append(event.name)

        total = Booking.objects.filter(event=event).aggregate(
            total=Sum('seats_booked')
        )['total'] or 0

        booking_counts.append(total)

    return render(request, 'booking/dashboard.html', {
        'total_events': total_events,
        'total_bookings': total_bookings,
        'total_tickets_sold': total_tickets_sold,
        'total_revenue': total_revenue,
        'event_names': json.dumps(event_names),
        'booking_counts': json.dumps(booking_counts),
    })


@login_required
def artist_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    events = Event.objects.filter(name=event.name)

    return render(request, 'booking/artist_detail.html', {
        'artist': event,
        'events': events
    })


@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    event = booking.event
    event.available_seats += booking.seats_booked
    event.save()

    booking.delete()

    return redirect('history')


@staff_member_required
def use_ticket(request, booking_id):
    try:
        booking = Booking.objects.get(id=booking_id)

        if booking.is_used:
            return render(request, "verify.html", {
                "status": "used",
                "booking": booking
            })

        booking.is_used = True
        booking.save()

        return render(request, "verify.html", {
            "status": "success",
            "booking": booking
        })

    except Booking.DoesNotExist:
        return render(request, "verify.html", {
            "status": "invalid",
            "booking": None
        })


def contact(request):
    if request.method == "POST":
        name = request.POST.get("name")
        email = request.POST.get("email")
        message = request.POST.get("message")

        send_mail(
            subject=f"Support Request from {name}",
            message=message,
            from_email=email,
            recipient_list=[settings.EMAIL_HOST_USER],
        )

        return HttpResponse("Message sent successfully!")

    return render(request, "booking/contact.html")


def about(request):
    return render(request, 'booking/about.html')