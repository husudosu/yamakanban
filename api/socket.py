from flask_socketio import Namespace, emit, join_room
from flask_jwt_extended import jwt_required, current_user
from werkzeug.exceptions import Forbidden

from api.model.board import BoardAllowedUser


class BoardNamespace(Namespace):

    @jwt_required()
    def on_connect(self):
        print("Client connected")
        print("Current user: ")
        print(current_user.name)

    def on_disconnect(self):
        pass

    def on_my_event(self, data):
        print("My event", data)

    @jwt_required()
    def on_board_change(self, data):
        member = BoardAllowedUser.get_by_user_id(
            data["board_id"], current_user.id)
        # Check if user has access to board
        if not member:
            raise Forbidden()
        print(f"Subscribing to new board events: {data}")
        join_room(f"board-{data['board_id']}")
