from flask import Blueprint, request
from flask_jwt_extended import jwt_required, current_user

from api.app import db
from api.model.card import Card
from api.model.checklist import CardChecklist, ChecklistItem
from api.service import checklist as checklist_service
from api.util.schemas import CardChecklistSchema, ChecklistItemSchema

checklist_bp = Blueprint("checklist_bp", __name__)

checklist_schema = CardChecklistSchema()
checklist_new_schema = CardChecklistSchema(only=("title",))
checklist_item_schema = ChecklistItemSchema()


@checklist_bp.route("/card/<card_id>/checklist", methods=["POST"])
@jwt_required()
def post_checklist(card_id: int):
    checklist = checklist_service.post_card_checklist(
        current_user,
        Card.get_or_404(card_id),
        checklist_schema.load(request.json)
    )
    db.session.add(checklist)
    db.session.commit()
    return checklist_schema.dump(checklist)


@checklist_bp.route("/checklist/<checklist_id>", methods=["PATCH"])
@jwt_required()
def patch_checklist(checklist_id: int):
    checklist = checklist_service.patch_card_checklist(
        current_user,
        CardChecklist.get_or_404(checklist_id),
        checklist_schema.load(request.json)
    )
    db.session.commit()
    db.session.refresh(checklist)
    return checklist_schema.dump(checklist)


@checklist_bp.route("/checklist/<checklist_id>", methods=["DELETE"])
@jwt_required()
def delete_checklist(checklist_id: int):
    checklist_service.delete_card_checklist(
        current_user,
        CardChecklist.get_or_404(checklist_id)
    )
    db.session.commit()
    return {}


@checklist_bp.route("/checklist/<checklist_id>/item", methods=["POST"])
@jwt_required()
def post_checklist_item(checklist_id: int):
    item = checklist_service.post_checklist_item(
        current_user,
        CardChecklist.get_or_404(checklist_id),
        checklist_item_schema.load(request.json),
    )
    db.session.commit()
    db.session.refresh(item)
    return checklist_item_schema.dump(item)


@checklist_bp.route("/checklist/item/<item_id>", methods=["PATCH"])
@jwt_required()
def patch_checklist_item(item_id: int):
    item = checklist_service.patch_checklist_item(
        current_user,
        ChecklistItem.get_or_404(item_id),
        checklist_item_schema.load(request.json, partial=True)
    )
    db.session.commit()
    db.session.refresh(item)
    return checklist_item_schema.dump(item)


@checklist_bp.route("/checklist/item/<item_id>", methods=["DELETE"])
@jwt_required()
def delete_checklist_item(item_id: int):
    checklist_service.delete_checklist_item(
        current_user,
        ChecklistItem.get_or_404(item_id)
    )
    db.session.commit()
    return {}
