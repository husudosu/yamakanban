from crypt import methods
from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, current_user

from api.app import db
from api.model.card import Card, CardComment
from api.model.list import BoardList

from api.service import card as card_service
from api.util.schemas import CardActivitySchema, CardSchema, CardCommentSchema

card_bp = Blueprint("card_bp", __name__)

card_schema = CardSchema()
card_comment_schema = CardCommentSchema()
card_activity_schema = CardActivitySchema()


@card_bp.route("/list/<list_id>/card", methods=["GET"])
@jwt_required()
def get_list_cards(list_id: int):
    return jsonify(card_schema.dump(
        card_service.get_cards(
            current_user, BoardList.get_or_404(list_id)
        ),
        many=True
    ))


@card_bp.route("/list/<list_id>/card", methods=["POST"])
@jwt_required()
def post_list_card(list_id: int):
    card = card_service.post_card(
        current_user,
        BoardList.get_or_404(list_id),
        card_schema.load(request.json)
    )
    db.session.add(card)
    db.session.commit()
    db.session.refresh(card)
    return card_schema.dump(card)


@card_bp.route("/card/<card_id>", methods=["PATCH"])
@jwt_required()
def patch_list_card(card_id: int):
    updated_card = card_service.patch_card(
        current_user,
        Card.get_or_404(card_id),
        card_schema.load(request.json, partial=True)
    )
    db.session.commit()
    db.session.refresh(updated_card)

    return card_schema.dump(updated_card)


@card_bp.route("/card/<card_id>", methods=["GET"])
@jwt_required()
def get_card(card_id: int):
    card = card_service.get_card(current_user, card_id)
    return card_schema.dump(card)


@card_bp.route("/card/<card_id>", methods=["DELETE"])
@jwt_required()
def delete_list_card(card_id: int):
    card_service.delete_card(current_user, Card.get_or_404(card_id))
    db.session.commit()
    return {}


@card_bp.route("/card/<card_id>/comment", methods=["POST"])
@jwt_required()
def post_card_comment(card_id: int):
    activity = card_service.post_card_comment(
        current_user,
        Card.get_or_404(card_id),
        card_comment_schema.load(request.json)
    )
    db.session.commit()
    db.session.refresh(activity)
    return card_activity_schema.dump(activity)
    # return card_comment_schema.dump(activity)


@card_bp.route("/comment/<comment_id>", methods=["PATCH"])
@jwt_required()
def patch_card_comment(comment_id: int):
    updated_comment = card_service.patch_card_comment(
        current_user,
        CardComment.get_or_404(comment_id),
        card_comment_schema.load(request.json, partial=True)
    )
    db.session.commit()
    db.session.refresh(updated_comment)
    return card_comment_schema.dump(updated_comment)


@card_bp.route("/comment/<comment_id>", methods=["DELETE"])
@jwt_required()
def delete_card_comment(comment_id: int):
    card_service.delete_card_comment(
        current_user,
        CardComment.get_or_404(comment_id)
    )
    db.session.commit()
    return {}


@card_bp.route("/card/<card_id>/activities", methods=["GET"])
@jwt_required()
def get_card_activities(card_id: int):
    return jsonify(card_activity_schema.dump(card_service.get_card_activities(
        current_user,
        Card.get_or_404(card_id)
    ), many=True))


@card_bp.route("/card/<card_id>/checklist", methods=["POST"])
@jwt_required()
def post_checklist(card_id: int):
    raise NotImplemented()


@card_bp.route("/checklist/<checklist_id>", methods=["DELETE"])
@jwt_required()
def delete_checklist(checklist_id: int):
    raise NotImplemented()


@card_bp.route("/checklist/<checklist_id>/item", methods=["POST"])
@jwt_required()
def post_checklist_item(checklist_id: int):
    raise NotImplemented()


@card_bp.route("/checklist/item/<item_id>", methods=["PATCH"])
@jwt_required()
def patch_checklist_item(item_id: int):
    raise NotImplemented()


@card_bp.route("/checklist/item/<item_id>", methods=["DELETE"])
@jwt_required()
def delete_checklist_item(item_id: int):
    raise NotImplemented()
