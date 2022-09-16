from flask import Blueprint, jsonify, request, abort
from flask_jwt_extended import jwt_required, current_user
from webargs.flaskparser import use_args
from werkzeug.exceptions import Forbidden

from api.app import db
from api.model.board import BoardAllowedUser
from api.model.card import Card, CardComment
from api.model.list import BoardList

from api.service import card as card_service
from api.util.schemas import (
    CardActivityPaginatedSchema, CardActivityQuerySchema,
    CardActivitySchema, CardSchema, CardCommentSchema,
)

card_bp = Blueprint("card_bp", __name__)

card_schema = CardSchema()
card_comment_schema = CardCommentSchema()
card_activity_schema = CardActivitySchema()
card_activity_paginated_schema = CardActivityPaginatedSchema()
activity_schema_query = CardActivityQuerySchema()


@card_bp.route("/card/<card_id>", methods=["GET"])
@jwt_required()
def get_card(card_id: int):
    card: Card = Card.get_or_404(card_id)
    if BoardAllowedUser.get_by_user_id(card.board_id, current_user.id):
        return card_schema.dump(card)
    raise Forbidden()


@card_bp.route("/list/<list_id>/card", methods=["GET"])
@jwt_required()
def get_list_cards(list_id: int):
    board_list: BoardList = BoardList.get_or_404(list_id)
    if BoardAllowedUser.get_by_user_id(board_list.board_id, current_user.id):
        return jsonify(card_schema.dump(
            board_list.cards,
            many=True
        ))
    raise Forbidden()


@card_bp.route("/list/<list_id>/card", methods=["POST"])
@jwt_required()
def post_list_card(list_id: int):
    board_list: BoardList = BoardList.get_or_404(list_id)
    current_member = BoardAllowedUser.get_by_user_id(
        board_list.board_id, current_user.id)
    print("Current member not found")
    if not current_member:
        raise Forbidden()

    card = card_service.post_card(
        current_member,
        board_list,
        card_schema.load(request.json)
    )
    db.session.add(card)
    db.session.commit()
    db.session.refresh(card)
    return card_schema.dump(card)


@card_bp.route("/card/<card_id>", methods=["PATCH"])
@jwt_required()
def patch_list_card(card_id: int):
    card: Card = Card.get_or_404(card_id)
    current_member = BoardAllowedUser.get_by_user_id(
        card.board_id, current_user.id)

    if not current_member:
        raise Forbidden()

    updated_card = card_service.patch_card(
        current_member,
        card,
        card_schema.load(request.json, partial=True)
    )
    db.session.commit()
    db.session.refresh(updated_card)

    return card_schema.dump(updated_card)


@card_bp.route("/card/<card_id>", methods=["DELETE"])
@jwt_required()
def delete_list_card(card_id: int):
    card: Card = Card.get_or_404(card_id)
    current_member = BoardAllowedUser.get_by_user_id(
        card.board_id, current_user.id
    )
    if not current_member:
        raise Forbidden()

    card_service.delete_card(current_member, card)
    db.session.commit()
    return {}


@card_bp.route("/card/<card_id>/comment", methods=["POST"])
@jwt_required()
def post_card_comment(card_id: int):
    card: Card = Card.get_or_404(card_id)
    current_member: BoardAllowedUser = BoardAllowedUser.get_by_user_id(
        card.board_id, current_user.id)

    if not current_member:
        raise Forbidden()

    activity = card_service.post_card_comment(
        current_member,
        card,
        card_comment_schema.load(request.json)
    )
    db.session.commit()
    db.session.refresh(activity)
    return card_activity_schema.dump(activity)


@card_bp.route("/comment/<comment_id>", methods=["PATCH"])
@jwt_required()
def patch_card_comment(comment_id: int):
    comment: CardComment = CardComment.get_or_404(comment_id)
    current_member = BoardAllowedUser.get_by_user_id(
        comment.board_id, current_user.id)

    if not current_member:
        raise Forbidden()

    updated_comment = card_service.patch_card_comment(
        current_member,
        comment,
        card_comment_schema.load(request.json, partial=True)
    )
    db.session.commit()
    db.session.refresh(updated_comment)
    return card_comment_schema.dump(updated_comment)


@card_bp.route("/comment/<comment_id>", methods=["DELETE"])
@jwt_required()
def delete_card_comment(comment_id: int):
    comment: CardComment = CardComment.get_or_404(comment_id)
    current_member = BoardAllowedUser.get_by_user_id(
        comment.board_id, current_user.id
    )

    if not current_member:
        raise Forbidden()
    card_service.delete_card_comment(
        current_user,
        CardComment.get_or_404(comment_id)
    )
    db.session.commit()
    return {}


@card_bp.route("/card/<card_id>/activities", methods=["GET"])
@jwt_required()
@use_args(activity_schema_query, location="query")
def get_card_activities(args, card_id: int):
    card: Card = Card.get_or_404(card_id)
    current_member = BoardAllowedUser.get_by_user_id(
        card.board_id, current_user.id)

    if not current_member:
        raise Forbidden()

    return card_activity_paginated_schema.dump(
        card_service.get_card_activities(
            card,
            args
        )
    )


@card_bp.route("/card/<card_id>/member", methods=["POST"])
@jwt_required()
def assign_member(card_id: int):
    raise NotImplemented()
    card: Card = Card.get_or_404(card_id)
    member = card_service.assign_card_member(
        current_user,
        card,
        BoardAllowedUser.get_by_user_id(
            card.board_id, request.json["user_id"]) or abort(404, "User not member of board.")
    )
