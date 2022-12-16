from flask import request, Blueprint
from flask.views import MethodView
from flask_jwt_extended import current_user, jwt_required

from api.service.list import list_service
from api.util.dto import ListDTO

list_bp = Blueprint("list_bp", __name__)


class ListAPI(MethodView):
    decorators = [jwt_required()]

    def get(self, board_id: int):
        return ListDTO.lists_schema.dump(
            list_service.get(current_user, board_id), many=True
        )

    def post(self, board_id: int):
        return ListDTO.lists_schema.dump(
            list_service.post(current_user, board_id,
                              ListDTO.lists_schema.load(request.json))
        )

    def patch(self, list_id: int):
        return ListDTO.update_list_schema.dump(
            list_service.patch(current_user, list_id,
                               ListDTO.update_list_schema.load(request.json, partial=True))
        )

    def delete(self, list_id: int):
        list_service.delete(current_user, list_id)
        return {"message": "List deleted."}


class ListCardOrderAPI(MethodView):
    decorators = [jwt_required()]

    def patch(self, list_id: int):
        list_service.update_cards_position(current_user, list_id, request.json)
        return {}


list_view = ListAPI.as_view("list-view")
list_card_order_view = ListCardOrderAPI.as_view("list-card-order-view")

list_bp.add_url_rule("/board/<board_id>/list",
                     methods=["GET", "POST"], view_func=list_view)
list_bp.add_url_rule("/list/<list_id>",
                     methods=["PATCH", "DELETE"], view_func=list_view)
list_bp.add_url_rule("/list/<list_id>/cards-order",
                     methods=["PATCH"], view_func=list_card_order_view)
