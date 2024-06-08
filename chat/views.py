from .models import Room, User, Message
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json


import base64
from django.core.files.base import ContentFile
from .models import User, Room, Message
from django.db import IntegrityError


@csrf_exempt
def create_user(request):
    if request.method == "POST":
        try:
            data_user = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "Invalid JSON data"}, status=400)

        user_name = data_user.get("name")
        user_image = data_user.get("image")

        if not user_name or not user_image:
            return JsonResponse({"status": "error", "message": "Name and image are required fields"}, status=400)

        try:
            image_binary_data = base64.b64decode(user_image)
        except (base64.binascii.Error, TypeError):
            return JsonResponse({"status": "error", "message": "Invalid base64 image data"}, status=400)

        image_content = ContentFile(image_binary_data, name=f'{user_name}.png')

        try:
            User.objects.create(user_name=user_name, user_image=image_content)
        except IntegrityError:
            return JsonResponse({"status": "error", "message": f"{user_name} with this name already exists"}, status=400)

        return JsonResponse({"status": "success", "message": f"{user_name} created successfully"}, status=201)
    else:
        return JsonResponse({"status": "error", "message": "Invalid request method"}, status=405)


@csrf_exempt
def room(request):
    if request.method == "POST":
        try:
            data_room = json.loads(request.body)
            name = data_room.get("name")

            if Room.objects.filter(name=name).exists():
                return JsonResponse({"error": "Room name already exists"}, status=400)
            else:
                Room.objects.create(name=name)
                return JsonResponse({"success": "Room created successfully"}, status=201)
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    elif request.method == "GET":
        try:
            rooms = Room.objects.all().values('id', 'name')
            rooms_list = list(rooms)
            return JsonResponse({"rooms": rooms_list}, status=200)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    else:
        return JsonResponse({"error": "Invalid HTTP method"}, status=405)


@csrf_exempt
def check_user(request):
    if request.method == 'POST':
        try:
            data_room = json.loads(request.body)
            name = data_room.get("name")
            user = User.objects.get(user_name=name)
            user_id = user.id
            return JsonResponse({"message": "User found.", "data": user_id})
        except User.DoesNotExist:
            return JsonResponse({"error": "User does not exist.", }, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)})


@csrf_exempt
def add_members_to_room(request, room_id):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            member_ids = data.get("user_id", [])

            room = Room.objects.get(pk=room_id)

            existing_members = room.members.all()
            new_members = User.objects.filter(
                pk__in=member_ids).exclude(pk__in=existing_members)

            room.members.add(*new_members)

            return JsonResponse({"success": "Members added to the room successfully"}, status=200)
        except Room.DoesNotExist:
            return JsonResponse({"error": "Room does not exist"}, status=404)
        except User.DoesNotExist:
            return JsonResponse({"error": "One or more users do not exist"}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Invalid HTTP method"}, status=405)


@csrf_exempt
def get_all_messages_in_room(request, room_id):
    if request.method == "GET":
        try:
            room = Room.objects.get(pk=room_id)

            room_members = room.members.all()

            all_messages = []

            for member in room_members:
                member_messages = Message.objects.filter(
                    room_id=room_id, user=member)

                # Get user's name and image
                user_name = member.user_name
                user_image = member.user_image.url if member.user_image else None

                # Iterate through messages and add user information
                for message in member_messages:
                    message_data = {
                        "message": message.message,
                        "timestamp": message.timestamp,
                        "user_name": user_name,
                        "user_image": user_image,
                        "id": message.id
                    }
                    all_messages.append(message_data)

            # Sort messages by timestamp
            all_messages.sort(key=lambda x: x['timestamp'])

            return JsonResponse({"messages": all_messages}, status=200)

        except Room.DoesNotExist:
            return JsonResponse({"error": "Room does not exist"}, status=404)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    else:
        return JsonResponse({"error": "Invalid HTTP method"}, status=405)
