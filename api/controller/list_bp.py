from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, current_user

from api.app import db, socketio
from werkzeug.exceptions import Forbidden
from api.model.board import Board, BoardAllowedUser
from api.model.list import BoardList

from api.service import list as list_service
from api.util.schemas import BoardListSchema

list_bp = Blueprint("list_bp", __name__)

board_lists_schema = BoardListSchema()


@list_bp.route("/board/<board_id>/list", methods=["GET"])
@jwt_required()
def get_lists(board_id: int):
    board: Board = Board.get_or_404(board_id)
    current_member = BoardAllowedUser.get_by_user_id(board.id, current_user.id)
    if not current_member:
        raise Forbidden()

    return jsonify(board_lists_schema.dump(board.lists, many=True))


@list_bp.route("/board/<board_id>/list", methods=["POST"])
@jwt_required()
def post_list(board_id: int):
    board: Board = Board.get_or_404(board_id)
    current_member = BoardAllowedUser.get_by_user_id(board.id, current_user.id)
    if not current_member:
        raise Forbidden()

    board_list = list_service.post_board_list(
        current_member,
        board,
        board_lists_schema.load(request.json)
    )
    db.session.add(board_list)
    db.session.commit()
    db.session.refresh(board_list)
    dmp = board_lists_schema.dump(board_list)

    socketio.emit(
        "list.new",
        dmp,
        namespace="/board",
        to=f"board-{board_list.board_id}"
    )

    return dmp


@list_bp.route("/list/<list_id>", methods=["PATCH"])
@jwt_required()
def patch_list(list_id: int):
    board_list: BoardList = BoardList.get_or_404(list_id)
    current_member = BoardAllowedUser.get_by_user_id(
        board_list.board_id, current_user.id)
    if not current_member:
        raise Forbidden()

    updated_list = list_service.patch_board_list(
        current_member,
        board_list,
        board_lists_schema.load(request.json, partial=True)
    )
    db.session.commit()
    db.session.refresh(updated_list)
    dmp = board_lists_schema.dump(updated_list)
    socketio.emit(
        "list.update",
        dmp,
        namespace="/board",
        to=f"board-{board_list.board_id}"
    )
    return dmp


@list_bp.route("/list/<list_id>", methods=["DELETE"])
@jwt_required()
def delete_list(list_id: int):
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
    db.session.commit()

    socketio.emit(
        "list.delete",
        dmp,
        namespace="/board",
        to=f"board-{board_list.board_id}"
    )
    return {}


@list_bp.route("/list/<list_id>/cards-order", methods=["PATCH"])
@jwt_required()
def patch_card_order(list_id: int):
    board_list: BoardList = BoardList.get_or_404(list_id)
    current_member = BoardAllowedUser.get_by_user_id(
        board_list.board_id, current_user.id)
    if not current_member:
        raise Forbidden()

    list_service.update_cards_position(
        current_member, BoardList.get_or_404(list_id), request.json)
    db.session.commit()
    socketio.emit(
        "card.update.order",
        {"order": request.json, "list_id": board_list.id},
        namespace="/board",
        to=f"board-{board_list.board_id}"
    )
    return {}
