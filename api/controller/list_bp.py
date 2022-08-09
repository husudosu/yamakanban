from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, current_user


from api.app import db
from api.model.board import Board
from api.model.list import BoardList

from api.service import list as list_service
from api.util.schemas import BoardListSchema

list_bp = Blueprint("list_bp", __name__)

board_lists_schema = BoardListSchema()


@list_bp.route("/board/<board_id>/list", methods=["GET"])
@jwt_required()
def get_lists(board_id: int):
    return jsonify(board_lists_schema.dump(
        list_service.get_board_lists(
            current_user,
            Board.get_or_404(board_id)
        ),
        many=True
    ))


@list_bp.route("/board/<board_id>/list", methods=["POST"])
@jwt_required()
def post_list(board_id: int):
    board_list = list_service.post_board_list(
        current_user,
        Board.get_or_404(board_id),
        board_lists_schema.load(request.json)
    )
    db.session.add(board_list)
    db.session.commit()
    db.session.refresh(board_list)
    return board_lists_schema.dump(board_list)


@list_bp.route("/list/<list_id>", methods=["PATCH"])
@jwt_required()
def patch_list(list_id: int):
    updated_list = list_service.patch_board_list(
        current_user,
        BoardList.get_or_404(list_id),
        board_lists_schema.load(request.json, partial=True)
    )
    db.session.commit()
    db.session.refresh(updated_list)
    return board_lists_schema.dump(updated_list)


@list_bp.route("/list/<list_id>", methods=["DELETE"])
@jwt_required()
def delete_list(list_id: int):
    list_service.delete_board_list(
        current_user,
        BoardList.get_or_404(list_id)
    )
    db.session.commit()
    return {}


@list_bp.route("/list/<list_id>/cards-order", methods=["PATCH"])
@jwt_required()
def patch_card_order(list_id: int):
    list_service.update_cards_position(
        current_user, BoardList.get_or_404(list_id), request.json)
    db.session.commit()
    return {}
