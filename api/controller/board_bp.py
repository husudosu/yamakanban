
import sqlalchemy as sqla
from flask_jwt_extended import current_user, jwt_required

from flask import Blueprint, request, jsonify, abort
from api.model.board import Board, BoardAllowedUser, BoardRole
from ..model.user import User
from api.service import board as board_service
from api.util.schemas import (
    BoardAllowedUserSchema, BoardRoleSchema, BoardSchema
)

from api.app import db

board_bp = Blueprint("board_bp", __name__)

board_schema = BoardSchema()
boards_schema = BoardSchema(exclude=("lists",))
board_allowed_user_schema = BoardAllowedUserSchema()
board_roles_schema = BoardRoleSchema()


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


@board_bp.route("/board/<board_id>/roles")
@jwt_required()
def get_board_roles(board_id: int):
    return jsonify(board_roles_schema.dump(
        board_service.get_board_roles(
            current_user,
            Board.get_or_404(board_id)
        ),
        many=True
    ))


@board_bp.route("/board/<board_id>/member", methods=["POST"])
@jwt_required()
def add_board_member(board_id: int):
    data = board_allowed_user_schema.load(request.json)

    # Check if the provided board_role_id is assigned to our board.
    role = BoardRole.query.filter(
        sqla.and_(
            BoardRole.id == data["board_role_id"],
            BoardRole.board_id == board_id
        )
    ).first()
    if not role:
        abort(404, "Board role not exists.")
    member = board_service.add_member(
        current_user,
        Board.get_or_404(board_id),
        User.get_or_404(data["user_id"]),
        role
    )
    db.session.commit()
    return board_allowed_user_schema.dump(member)


@board_bp.route("/board/<board_id>/member", methods=["DELETE"])
@jwt_required()
def delete_board_member(board_id: int):
    data = board_allowed_user_schema.load(request.json, partial=True)
    board_service.remove_member(
        current_user,
        Board.get_or_404(board_id),
        User.get_or_404(data["user_id"])
    )
    return {}
