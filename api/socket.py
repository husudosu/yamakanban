import enum
from flask_socketio import Namespace, join_room, leave_room, rooms
from flask_jwt_extended import current_user, jwt_required
from flask import current_app


class SIOEvent(enum.Enum):
    """Socket.IO events"""

    CARD_NEW = "card.new"
    CARD_REVERT = "card.revert"
    CARD_UPDATE = "card.update"
    CARD_ARCHIVE = "card.archive"
    CARD_DELETE = "card.delete"

    CARD_UPDATE_ORDER = "card.update.order"

    CARD_MEMBER_ASSIGNED = "card.member.assigned"
    CARD_MEMBER_DEASSIGNED = "card.member.deassigned"

    CARD_DATE_NEW = "card.date.new"
    CARD_DATE_UPDATE = "card.date.update"
    CARD_DATE_DELETE = "card.data.delete"

    CARD_CHECKLIST_NEW = "card.checklist.new"
    CARD_CHECKLIST_UPDATE = "card.checklist.update"
    CARD_CHECKLIST_DELETE = "card.checklist.delete"

    CHECKLIST_ITEM_NEW = "checklist.item.new"
    CHECKLIST_ITEM_UPDATE = "checklist.item.update"
    CHECKLIST_ITEM_DELETE = "checklist.item.delete"

    CHECKLIST_ITEM_UPDATE_ORDER = "checklist.item.update.order"

    CARD_ACTIVITY = "card.activity"
    # These two currently used for only card comments
    CARD_ACTIVITY_UPDATE = "card.activity.update"
    CARD_ACTIVITY_DELETE = "card.activity.delete"

    LIST_NEW = "list.new"
    LIST_REVERT = "list.revert"
    LIST_UPDATE_ORDER = "list.update.order"
    LIST_UPDATE = "list.update"
    LIST_ARCHIVE = "list.archive"
    LIST_DELETE = "list.delete"


class BoardNamespace(Namespace):

    @jwt_required()
    def on_connect(self):
        current_app.logger.debug(
            f"Client connected identity: {current_user.username}.")

    def on_disconnect(self):
        current_app.logger.debug("Client disconnected.")

    @jwt_required()
    def on_board_change(self, data):
        room_name = f"board-{data['board_id']}"
        current_app.logger.debug(
            f"Subscribing to new board events: {data}")
        # Leave all other board rooms

        for room in rooms():
            if room.startswith("board"):
                current_app.logger.debug(
                    f"Trafalgar Law: Leaving Board ROOM {room} SHAMBLES!")
                leave_room(room)
        join_room(room_name)
        current_app.logger.debug(rooms())

    @jwt_required()
    def on_card_change(self, data):
        room_name = f"card-{data['card_id']}"
        current_app.logger.debug(f"Subscribing to new card events: {data}")
        # Leave all other card rooms
        for room in rooms():
            if room.startswith("card"):
                current_app.logger.debug(
                    f"Trafalgar Law: Leaving Card ROOM {room} SHAMBLES!")
                leave_room(room)
        join_room(room_name)
        current_app.logger.debug(rooms())
