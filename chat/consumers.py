import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Room, Message, User


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = f"room_{
            self.scope['url_route']['kwargs']['room_name']}"
        await self.channel_layer.group_add(self.room_name, self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.room_name, self.channel_name)

    async def chat_message(self, event):
        event["timestamp"] = event["timestamp"].strftime('%Y-%m-%d %H:%M:%S')
        await self.send(text_data=json.dumps(event))

    async def receive(self, text_data):
        event = json.loads(text_data)
        event_type = event.get('type', None)
        print(event)
        if event_type == "fetch_messages":
            return

        else:
            await self.create_message(data=event)
            messages = await self.get_messages(event['room_id'], event["user_id"])
            user = await self.get_user(event["user_id"])
            await self.send_all_messages(event['room_id'])
            if not user:
                await self.send(text_data=json.dumps({"error": "User not found"}))
                return

            messages_list = [
                {
                    "id": message["id"],
                    "message": message["message"],
                    "timestamp": message["timestamp"].strftime('%Y-%m-%d %H:%M:%S'),
                    "user_name": user["user_name"],
                    "user_image": "/media/" + user["user_image"]
                }
                for message in messages
            ]

            await self.send(text_data=json.dumps({"messages": messages_list}))

    async def send_all_messages(self, room_id):
        messages = await self.get_all_messages_in_room(room_id)

        if isinstance(messages, str):
            await self.send(text_data=json.dumps({"error": messages}))
        else:
            await self.send(text_data=json.dumps({"messages": messages}))

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

    async def broadcast_message(self, message):
        await self.channel_layer.group_send(
            self.room_name,
            {
                "type": "chat.message",
                "message": message.message,
                "timestamp": message.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                "user_name": message.user.user_name,
                "user_image": "/media/" + message.user.user_image.url if message.user.user_image else None,
                "id": message.id
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
