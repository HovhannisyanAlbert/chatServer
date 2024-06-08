from django.urls import path
from . import views
urlpatterns = [
    path('', views.create_user),
    path("room/", views.room),
    path("check-user/", views.check_user),
    path("<int:room_id>/join/", views.add_members_to_room),
    path('<int:room_id>/messages/', views.get_all_messages_in_room),


]
