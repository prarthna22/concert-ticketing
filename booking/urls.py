from django.urls import path
from . import views

urlpatterns = [

    path('', views.event_list, name='event_list'),

    path('book/<int:event_id>/', views.book_ticket, name='book_ticket'),

    path('payment/<int:event_id>/', views.process_payment, name='payment'),
    path('pay/<int:event_id>/', views.process_payment, name='pay'),

    path('success/', views.success, name='success'),

    path('signup/', views.signup, name='signup'),

    path('download-ticket/<int:booking_id>/', views.download_ticket, name='download_ticket'),

    path('artist/<int:event_id>/', views.artist_detail, name='artist_detail'),

    path('history/', views.booking_history, name='history'),

    path('create-event/', views.create_event, name='create_event'),
    path('edit-event/<int:event_id>/', views.edit_event, name='edit_event'),
    path('delete-event/<int:event_id>/', views.delete_event, name='delete_event'),

    path('dashboard/', views.dashboard, name='dashboard'),

    path('cancel-booking/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    
    path('use-ticket/<int:booking_id>/', views.use_ticket, name='use_ticket'),
    path('contact/', views.contact, name='contact'),
    path('about/', views.about, name='about'),

]