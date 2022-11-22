from werkzeug.exceptions import Forbidden

from flask import request, Blueprint
from flask.views import MethodView
from flask_jwt_extended import current_user, jwt_required

from api.util.dto import ChecklistDTO
from api.service.checklist import checklist_service, checklist_item_service

checklist_bp = Blueprint("checklist_bp", __name__)


class ChecklistAPI(MethodView):
    decorators = [jwt_required()]

    def post(self, card_id: int):
        return ChecklistDTO.checklist_schema.dump(
            checklist_service.post(
                current_user,
                card_id,
                ChecklistDTO.checklist_new_schema.load(request.json)
            )
        )

    def patch(self, checklist_id: int):
        return ChecklistDTO.checklist_schema.dump(
            checklist_service.patch(
                current_user,
                checklist_id,
                ChecklistDTO.checklist_schema.load(request.json)
            )
        )

    def delete(self, checklist_id: int):
        checklist_service.delete(current_user, checklist_id)
        return {"message": "Checklist deleted."}


class ChecklistItemAPI(MethodView):
    decorators = [jwt_required()]

    def post(self, checklist_id: int):
        return ChecklistDTO.checklist_item_schema.dump(
            checklist_item_service.post(
                current_user,
                checklist_id,
                ChecklistDTO.checklist_item_schema.load(request.json)
            )
        )

    def patch(self, item_id: int):
        return ChecklistDTO.checklist_item_schema.dump(
            checklist_item_service.patch(
                current_user,
                item_id,
                ChecklistDTO.checklist_item_schema.load(
                    request.json, partial=True)
            )
        )

    def delete(self, item_id: int):
        checklist_item_service.delete(
            current_user,
            item_id
        )
        return {"message": "Checklist item deleted."}


class ChecklistItemOrderAPI(MethodView):
    decorators = [jwt_required()]

    def patch(self, checklist_id: int):
        checklist_item_service.update_items_position(
            current_user, checklist_id, request.json)
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
