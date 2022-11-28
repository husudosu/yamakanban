from werkzeug.exceptions import Forbidden

from flask import jsonify, request, Blueprint
from flask.views import MethodView
from flask_jwt_extended import current_user, jwt_required
import sqlalchemy.orm as sqla_orm

from api.app import socketio
from api.model.board import Board, BoardAllowedUser
from api.model.list import BoardList
from api.socket import SIOEvent

from api.util.schemas import BoardListSchema

import api.service.list as list_service

list_bp = Blueprint("list_bp", __name__)

board_lists_schema = BoardListSchema()
update_board_list_schema = BoardListSchema(exclude=("cards",))


class ListAPI(MethodView):
    decorators = [jwt_required()]

    def get(self, board_id: int):
        board: Board = Board.get_or_404(board_id)
        current_member = BoardAllowedUser.get_by_user_id(
            board.id, current_user.id)
        if not current_member:
            raise Forbidden()
        return jsonify(board_lists_schema.dump(board.lists, many=True))

    def post(self, board_id: int):
        board: Board = Board.get_or_404(board_id)
        current_member = BoardAllowedUser.get_by_user_id(
            board.id, current_user.id)
        if not current_member:
            raise Forbidden()

        board_list = list_service.post_board_list(
            current_member,
            board,
            board_lists_schema.load(request.json)
        )

        dmp = board_lists_schema.dump(board_list)

        socketio.emit(
            SIOEvent.LIST_NEW.value,
            dmp,
            namespace="/board",
            to=f"board-{board_list.board_id}"
        )

        return dmp

    def patch(self, list_id: int):
        board_list: BoardList = BoardList.get_or_404(list_id)
        current_member = BoardAllowedUser.get_by_user_id(
            board_list.board_id, current_user.id)
        if not current_member:
            raise Forbidden()

        updated_list = list_service.patch_board_list(
            current_member,
            board_list,
            update_board_list_schema.load(request.json, partial=True)
        )

        dmp = update_board_list_schema.dump(updated_list)
        socketio.emit(
            SIOEvent.LIST_UPDATE.value,
            dmp,
            namespace="/board",
            to=f"board-{board_list.board_id}"
        )
        return dmp

    def delete(self, list_id: int):
        board_list: BoardList = BoardList.get_or_404(list_id)
        current_member = BoardAllowedUser.get_by_user_id(
            board_list.board_id, current_user.id)
        if not current_member:
            raise Forbidden()

        list_service.delete_board_list(
            current_member,
            board_list
        )
        dmp = board_lists_schema.dump(board_list)

        socketio.emit(
            SIOEvent.LIST_DELETE.value,
            dmp,
            namespace="/board",
            to=f"board-{board_list.board_id}"
        )
        return {}


class ListCardOrderAPI(MethodView):
    decorators = [jwt_required()]

    def patch(self, list_id: int):
        board_list: BoardList = BoardList.get_or_404(list_id)
        current_member = BoardAllowedUser.get_by_user_id(
            board_list.board_id, current_user.id)
        if not current_member:
            raise Forbidden()

        list_service.update_cards_position(
            current_member, BoardList.get_or_404(list_id), request.json)

        socketio.emit(
            SIOEvent.CARD_UPDATE_ORDER.value,
            {"order": request.json, "list_id": board_list.id},
            namespace="/board",
            to=f"board-{board_list.board_id}"
        )
        return {}


list_view = ListAPI.as_view("list-view")
list_card_order_view = ListCardOrderAPI.as_view("list-card-order-view")

list_bp.add_url_rule("/board/<board_id>/list",
                     methods=["GET", "POST"], view_func=list_view)
list_bp.add_url_rule("/list/<list_id>",
                     methods=["PATCH", "DELETE"], view_func=list_view)
list_bp.add_url_rule("/list/<list_id>/cards-order",
                     methods=["PATCH"], view_func=list_card_order_view)
