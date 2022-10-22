from flask_socketio import Namespace, emit, join_room, leave_room, rooms
from flask import current_app


class BoardNamespace(Namespace):

    def on_connect(self):
        print("Client connected")

    def on_disconnect(self):
        pass

    def on_my_event(self, data):
        print("My event", data)

    def on_board_change(self, data):
        current_app.logger.debug(f"Subscribing to new board events: {data}")
        join_room(f"board-{data['board_id']}")
        current_app.logger.debug(rooms())
