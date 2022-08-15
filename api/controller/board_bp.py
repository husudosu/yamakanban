from flask_jwt_extended import current_user, jwt_required

from flask import Blueprint, request, jsonify
from api.model.board import Board
from api.service import board as board_service
from api.util.schemas import BoardAllowedUserSchema, BoardSchema

from api.app import db

board_bp = Blueprint("board_bp", __name__)

board_schema = BoardSchema()
boards_schema = BoardSchema(exclude=("lists",))
board_allowed_user_schema = BoardAllowedUserSchema()


@board_bp.route("/board")
@jwt_required()
def get_boards():
    return jsonify(boards_schema.dump(
        board_service.get_user_boards(current_user),
        many=True,
    ))


@board_bp.route("/board", methods=["POST"])
@jwt_required()
def post_board():
    board = board_service.post_board(
        current_user,
        board_schema.load(request.json)
    )
    db.session.add(board)
    db.session.commit()
    db.session.refresh(board)
    return board_schema.dump(board)


@board_bp.route("/board/<board_id>", methods=["PATCH"])
@jwt_required()
def patch_board(board_id: int):
    updated_board = board_service.patch_board(
        current_user,
        Board.get_or_404(board_id),
        board_schema.load(request.json)
    )
    db.session.commit()
    db.session.refresh(updated_board)
    return board_schema.dump(updated_board)


@board_bp.route("/board/<board_id>", methods=["DELETE"])
@jwt_required()
def delete_board(board_id: int):
    board_service.delete_board(current_user, Board.get_or_404(board_id))
    db.session.commit()
    return {}


@board_bp.route("/board/<board_id>", methods=["GET"])
@jwt_required()
def get_board(board_id: int):
    return board_schema.dump(
        board_service.get_board(current_user, board_id)
    )


@board_bp.route("/board/<board_id>/boardlists-order", methods=["PATCH"])
@jwt_required()
def patch_boardlists_order(board_id: int):
    board_service.update_boardlists_position(
        current_user,
        Board.get_or_404(board_id),
        request.json
    )
    db.session.commit()
    return {}


@board_bp.route("/board/<board_id>/user-claims", methods=["GET"])
@jwt_required()
def get_user_claims(board_id: int):
    return board_allowed_user_schema.dump(board_service.get_board_claims(
        current_user,
        Board.get_or_404(board_id)
    ))
