from flask import Blueprint, request
from flask.views import MethodView
from flask_jwt_extended import current_user, jwt_required
from webargs.flaskparser import use_args

from api.service.card import (
    card_service, comment_service, member_service, date_service
)
from api.util.dto import CardDTO

card_bp = Blueprint("card_bp", __name__)


class CardAPI(MethodView):
    decorators = [jwt_required()]

    @use_args(CardDTO.query_schema, location="query")
    def get(self, args, card_id: int):
        return CardDTO.card_schema.dump(
            card_service.get(current_user, card_id, args)
        )

    def post(self, list_id: int):
        return CardDTO.card_schema.dump(
            card_service.post(
                current_user, list_id, CardDTO.card_schema.load(request.json)
            )
        )

    def patch(self, card_id: int):
        return CardDTO.update_card_schema.dump(card_service.patch(
            current_user,
            card_id,
            CardDTO.update_card_schema.load(request.json, partial=True)
        ))

    def delete(self, card_id: int):
        card_service.delete(current_user, card_id)
        return {"message": "Card deleted."}


class CardActivityAPI(MethodView):
    decorators = [jwt_required(), use_args(
        CardDTO.activity_schema_query, location="query")]

    def get(self, args, card_id: int):
        return CardDTO.activity_paginated_schema.dump(
            card_service.get_activities(
                current_user,
                card_id,
                args
            )
        )


class CardCommentAPI(MethodView):
    decorators = [jwt_required()]

    def post(self, card_id: int):
        return CardDTO.activity_schema.dump(comment_service.post(
            current_user, card_id,
            CardDTO.comment_schema.load(request.json)
        ))

    def patch(self, comment_id: int):
        return CardDTO.comment_schema.dump(comment_service.patch(
            current_user, comment_id, CardDTO.comment_schema.load(request.json)
        ))

    def delete(self, comment_id: int):
        comment_service.delete(current_user, comment_id)
        return {"message": "Comment deleted."}


class CardAssignMemberAPI(MethodView):
    decorators = [jwt_required()]

    def post(self, card_id: int):
        assignment = member_service.post(
            current_user, card_id, CardDTO.member_schema.load(request.json))

        return CardDTO.member_schema.dump(assignment)


class CardDeassignAPI(MethodView):
    decorators = [jwt_required()]

    def post(self, card_id: int):
        member_service.delete(
            current_user, card_id, request.json["board_user_id"]
        )
        return {"message": "Card member deassigned"}


class CardDateAPI(MethodView):
    decorators = [jwt_required()]

    def post(self, card_id: int):
        return CardDTO.date_schema.dump(date_service.post(
            current_user,
            card_id,
            CardDTO.date_schema.load(request.json)
        ))

    def patch(self, date_id: int):
        return CardDTO.date_schema.dump(
            date_service.patch(
                current_user,
                date_id,
                CardDTO.date_schema.load(request.json, partial=True)
            )
        )

    def delete(self, date_id: int):
        date_service.delete(current_user, date_id)
        return {"message": "Card date deleted"}


card_view = CardAPI.as_view("card-view")
card_activity_view = CardActivityAPI.as_view("card-activity-view")
card_comment_view = CardCommentAPI.as_view("card-comment-view")
card_assign_member_view = CardAssignMemberAPI.as_view(
    "card-assign-member-view")
card_deassign_member_view = CardDeassignAPI.as_view(
    "card-deassign-member-view")
card_date_view = CardDateAPI.as_view("card-date-view")

card_bp.add_url_rule("/card/<card_id>", view_func=card_view,
                     methods=["GET", "PATCH", "DELETE"])
card_bp.add_url_rule("/list/<list_id>/card",
                     view_func=card_view, methods=["POST"])

card_bp.add_url_rule("/card/<card_id>/activities",
                     view_func=card_activity_view, methods=["GET"])

card_bp.add_url_rule("/card/<card_id>/comment",
                     view_func=card_comment_view, methods=["POST"])
card_bp.add_url_rule("/comment/<comment_id>",
                     view_func=card_comment_view, methods=["PATCH", "DELETE"])

card_bp.add_url_rule("/card/<card_id>/assign-member",
                     view_func=card_assign_member_view, methods=["POST"])
card_bp.add_url_rule("/card/<card_id>/deassign-member",
                     view_func=card_deassign_member_view, methods=["POST"])

card_bp.add_url_rule("/card/<card_id>/date",
                     view_func=card_date_view, methods=["POST"])
card_bp.add_url_rule(
    "/date/<date_id>", view_func=card_date_view, methods=["PATCH", "DELETE"])
