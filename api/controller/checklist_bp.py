from werkzeug.exceptions import Forbidden

from flask import request, Blueprint
from flask.views import MethodView
from flask_jwt_extended import current_user, jwt_required

from api.app import db
from api.model.board import BoardAllowedUser
from api.model.card import Card
from api.model.checklist import CardChecklist, ChecklistItem
import api.service.checklist as checklist_service
from api.util.schemas import CardChecklistSchema, ChecklistItemSchema

checklist_bp = Blueprint("checklist_bp", __name__)

checklist_schema = CardChecklistSchema()
checklist_new_schema = CardChecklistSchema(only=("title",))
checklist_item_schema = ChecklistItemSchema()


class ChecklistAPI(MethodView):
    decorators = [jwt_required()]

    def post(self, card_id: int):
        card: Card = Card.get_or_404(card_id)
        current_member = BoardAllowedUser.get_by_user_id(
            card.board_id, current_user.id)
        if not current_member:
            raise Forbidden()

        checklist = checklist_service.post_card_checklist(
            current_member,
            card,
            checklist_schema.load(request.json)
        )
        db.session.add(checklist)
        db.session.commit()
        return checklist_schema.dump(checklist)

    def patch(self, checklist_id: int):
        checklist: CardChecklist = CardChecklist.get_or_404(checklist_id)
        current_member = BoardAllowedUser.get_by_user_id(
            checklist.board_id, current_user.id)
        if not current_member:
            raise Forbidden()

        checklist = checklist_service.patch_card_checklist(
            current_member,
            checklist,
            checklist_schema.load(request.json)
        )
        db.session.commit()
        db.session.refresh(checklist)
        return checklist_schema.dump(checklist)

    def delete(self, checklist_id: int):
        checklist: CardChecklist = CardChecklist.get_or_404(checklist_id)
        current_member = BoardAllowedUser.get_by_user_id(
            checklist.board_id, current_user.id)
        if not current_member:
            raise Forbidden()
        checklist_service.delete_card_checklist(
            current_member,
            checklist
        )
        db.session.commit()
        return {}


class ChecklistItemAPI(MethodView):
    decorators = [jwt_required()]

    def post(self, checklist_id: int):
        checklist: CardChecklist = CardChecklist.get_or_404(checklist_id)
        current_member = BoardAllowedUser.get_by_user_id(
            checklist.board_id, current_user.id)
        if not current_member:
            raise Forbidden()

        item = checklist_service.post_checklist_item(
            current_member,
            checklist,
            checklist_item_schema.load(request.json),
        )
        db.session.commit()
        db.session.refresh(item)
        return checklist_item_schema.dump(item)

    def patch(self, item_id: int):
        item: ChecklistItem = ChecklistItem.get_or_404(item_id)
        current_member = BoardAllowedUser.get_by_user_id(
            item.board_id, current_user.id)
        if not current_member:
            raise Forbidden()

        item = checklist_service.patch_checklist_item(
            current_member,
            item,
            checklist_item_schema.load(request.json, partial=True)
        )
        db.session.commit()
        db.session.refresh(item)
        return checklist_item_schema.dump(item)

    def delete(self, item_id: int):
        item: ChecklistItem = ChecklistItem.get_or_404(item_id)
        current_member = BoardAllowedUser.get_by_user_id(
            item.board_id, current_user.id)
        if not current_member:
            raise Forbidden()

        checklist_service.delete_checklist_item(current_member, item)

        db.session.commit()
        return {}


class ChecklistItemOrderAPI(MethodView):
    decorators = [jwt_required()]

    def patch(self, checklist_id: int):
        checklist: CardChecklist = CardChecklist.get_or_404(checklist_id)
        current_member = BoardAllowedUser.get_by_user_id(
            checklist.board_id, current_user.id)
        if not current_member:
            raise Forbidden()

        checklist_service.update_items_position(
            current_member,
            CardChecklist.get_or_404(checklist_id),
            request.json
        )
        db.session.commit()
        return {}


checklist_view = ChecklistAPI.as_view("checklist-view")
checklist_item_view = ChecklistItemAPI.as_view("checklist-item-view")
checklist_item_order_view = ChecklistItemOrderAPI.as_view(
    "checklist-item-order-view")

checklist_bp.add_url_rule("/card/<card_id>/checklist",
                          view_func=checklist_view, methods=["POST"])
checklist_bp.add_url_rule("/checklist/<checklist_id>",
                          view_func=checklist_view, methods=["PATCH", "DELETE"])

checklist_bp.add_url_rule("/checklist/<checklist_id>/item",
                          view_func=checklist_item_view, methods=["POST"])
checklist_bp.add_url_rule("/checklist/item/<item_id>", view_func=checklist_item_view,
                          methods=["PATCH", "DELETE"])

checklist_bp.add_url_rule("/checklist/<checklist_id>/items-order",
                          view_func=checklist_item_order_view, methods=["PATCH"])
