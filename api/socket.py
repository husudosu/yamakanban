import enum
from flask_socketio import Namespace, emit, join_room, leave_room, rooms
from flask import current_app


class SIOEvent(enum.Enum):
    """Socket.IO events"""

    CARD_NEW = "card.new"
    CARD_UPDATE = "card.update"
    CARD_DELETE = "card.delete"
    CARD_UPDATE_ORDER = "card.update.order"
    CARD_MEMBER_ASSIGNED = "card.member.assigned"
    CARD_MEMBER_DEASSIGNED = "card.member.deassigned"

    LIST_NEW = "list.new"
    LIST_UPDATE_ORDER = "list.update.order"
    LIST_UPDATE = "list.update"
    LIST_DELETE = "list.delete"


class BoardNamespace(Namespace):

    def on_connect(self):
        current_app.logger.info("Client connected.")

    def on_disconnect(self):
        current_app.logger.info("Client disconnected.")

    def on_board_change(self, data):
        room_name = f"board-{data['board_id']}"
        current_app.logger.debug(f"Subscribing to new board events: {data}")
        # Leave all other board rooms
        for room in rooms():
            if room.startswith("board"):
                current_app.logger.debug(
                    f"Trafalgar Law: Leaving ROOM {room} SHAMBLES!")
                leave_room(room)
        join_room(room_name)
        current_app.logger.debug(rooms())
