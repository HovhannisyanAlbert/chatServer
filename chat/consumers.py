import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Room, Message, User


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = f"room_{self.scope['url_route']['kwargs']['room_name']}"
        self.room_group_name = self.room_name
        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        event_type = data.get('type', None)

        if event_type == "fetch_messages":
            return

        else:
            # Create message and broadcast it
            await self.create_message(data)
            await self.broadcast_message(data)

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def create_message(self, data):
        user_id = data.get("user_id")
        room_name = data.get("room_name")

        if not room_name:
            return

        try:
            room = Room.objects.get(name=room_name)
        except Room.DoesNotExist:
            return

        message = Message.objects.create(
            room=room,
            user_id=user_id,
            message=data.get("message", ""),
        )

        return message

    async def broadcast_message(self, data):
        messages = await self.get_all_messages_in_room(data['room_id'])
        user = await self.get_user(data["user_id"])

        if not user:
            await self.send(text_data=json.dumps({"error": "User not found"}))
            return

        messages_list = [
            {
                "id": message["id"],
                "message": message["message"],
                "timestamp": message["timestamp"],
                "user_name": user["user_name"],
                "user_image": "/media/" + user["user_image"]
            }
            for message in messages
        ]

        # Improve this code by sending only the new message to the
        # client instead of fetching all messages when a new message is created, 

        # Use group_send to broadcast new message to all connected clients
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                "type": "chat.message",
                "messages": messages_list
            }
        )

    @database_sync_to_async
    def get_messages(self, room_id, user_id):
        return list(Message.objects.filter(room_id=room_id, user_id=user_id).values(
            "id", "message", "timestamp"))

    @database_sync_to_async
    def get_user(self, user_id):
        return User.objects.filter(id=user_id).values(
            "user_name", "user_image").first()

    @database_sync_to_async
    def get_all_messages_in_room(self, room_id):
        try:
            room = Room.objects.get(pk=room_id)
            room_members = room.members.all()

            all_messages = []

            for member in room_members:
                member_messages = Message.objects.filter(
                    room_id=room_id, user=member)

                user_name = member.user_name
                user_image = member.user_image.url if member.user_image else None

                for message in member_messages:
                    message_data = {
                        "message": message.message,
                        "timestamp": message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                        "user_name": user_name,
                        "user_image": user_image,
                        "id": message.id
                    }
                    all_messages.append(message_data)

            all_messages.sort(key=lambda x: x['timestamp'])
            return all_messages

        except Room.DoesNotExist:
            return "Room does not exist"
        except Exception as e:
            return str(e)
