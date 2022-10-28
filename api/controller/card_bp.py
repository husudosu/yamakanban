from werkzeug.exceptions import Forbidden
from webargs.flaskparser import use_args

from flask import Blueprint, request
from flask.views import MethodView
from flask_jwt_extended import jwt_required, current_user

from api.app import db, socketio
from api.model.board import BoardAllowedUser
from api.model.card import Card, CardComment, CardDate
from api.model.list import BoardList

from api.service import card as card_service
from api.socket import SIOEvent
from api.util.schemas import (
    CardActivityPaginatedSchema, CardActivityQuerySchema,
    CardActivitySchema, CardDateSchema, CardMemberSchema, CardSchema, CardCommentSchema,
)

card_bp = Blueprint("card_bp", __name__)

card_schema = CardSchema()
card_comment_schema = CardCommentSchema()
card_activity_schema = CardActivitySchema()
card_activity_paginated_schema = CardActivityPaginatedSchema()
card_member_schema = CardMemberSchema()
card_date_schema = CardDateSchema()
activity_schema_query = CardActivityQuerySchema()


class CardAPI(MethodView):
    decorators = [jwt_required()]

    def get(self, card_id: int):
        card: Card = Card.get_or_404(card_id)
        if BoardAllowedUser.get_by_user_id(card.board_id, current_user.id):
            return card_schema.dump(card)
        raise Forbidden()

    def post(self, list_id: int):
        board_list: BoardList = BoardList.get_or_404(list_id)
        current_member = BoardAllowedUser.get_by_user_id(
            board_list.board_id, current_user.id)
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

        # Dump and send Socket.IO event.
        dmp = card_schema.dump(card)
        socketio.emit(
            SIOEvent.CARD_NEW.value,
            dmp,
            namespace="/board",
            to=f"board-{card.board_id}"
        )
        return card_schema.dump(dmp)

    def patch(self, card_id: int):
        card: Card = Card.get_or_404(card_id)
        current_member = BoardAllowedUser.get_by_user_id(
            card.board_id, current_user.id)

        if not current_member:
            raise Forbidden()
        # Get card list id before update
        list_id = card.list_id

        updated_card = card_service.patch_card(
            current_member,
            card,
            card_schema.load(request.json, partial=True)
        )
        db.session.commit()
        db.session.refresh(updated_card)
        dmp = card_schema.dump(updated_card)
        socketio.emit(
            SIOEvent.CARD_UPDATE.value,
            {
                "card": dmp,
                "from_list_id": list_id
            },
            namespace="/board",
            to=f"board-{card.board_id}"
        )
        return dmp

    def delete(self, card_id: int):
        card: Card = Card.get_or_404(card_id)
        current_member = BoardAllowedUser.get_by_user_id(
            card.board_id, current_user.id
        )
        if not current_member:
            raise Forbidden()

        # Dump and send Socket.IO event.
        dmp = card_schema.dump(card)
        card_service.delete_card(current_member, card)
        db.session.commit()

        socketio.emit(
            SIOEvent.CARD_DELETE.value,
            dmp,
            namespace="/board",
            to=f"board-{card.board_id}"
        )
        return {}


class CardActivityAPI(MethodView):
    decorators = [jwt_required(), use_args(
        activity_schema_query, location="query")]

    def get(self, args, card_id: int):
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


class CardCommentAPI(MethodView):
    decorators = [jwt_required()]

    def post(self, card_id: int):
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

    def patch(self, comment_id: int):
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

    def delete(self, comment_id: int):
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


class CardAssignMemberAPI(MethodView):
    decorators = [jwt_required()]

    def post(self, card_id: int):
        card: Card = Card.get_or_404(card_id)
        current_member = BoardAllowedUser.get_by_user_id(
            card.board_id, current_user.id)

        if not current_member:
            raise Forbidden()

        assignment = card_service.assign_card_member(
            current_member, card, card_member_schema.load(request.json))
        db.session.commit()
        dmp = card_member_schema.dump(assignment)
        socketio.emit(
            SIOEvent.CARD_MEMBER_ASSIGNED.value,
            dmp,
            namespace="/board",
            to=f"board-{card.board_id}"
        )
        return card_member_schema.dump(assignment)


class CardDeassignAPI(MethodView):
    decorators = [jwt_required()]

    def post(self, card_id: int):
        card: Card = Card.get_or_404(card_id)
        current_member = BoardAllowedUser.get_by_user_id(
            card.board_id, current_user.id)

        if not current_member:
            raise Forbidden()
        card_service.deassign_card_member(
            current_member, card, card_member_schema.load(request.json)
        )
        # TODO: We need card_member here to pass into Socket.IO emit.
        db.session.commit()
        return {}


class CardDateAPI(MethodView):
    decorators = [jwt_required()]

    def post(self, card_id: int):
        card: Card = Card.get_or_404(card_id)
        current_member = BoardAllowedUser.get_by_user_id(
            card.board_id, current_user.id)

        if not current_member:
            raise Forbidden()
        card_date = card_service.post_card_date(
            current_member,
            card,
            card_date_schema.load(request.json)
        )
        db.session.commit()
        return card_date_schema.dump(card_date)

    def patch(self, date_id: int):
        card_date: CardDate = CardDate.get_or_404(date_id)
        current_member = BoardAllowedUser.get_by_user_id(
            card_date.board_id, current_user.id
        )

        if not current_member:
            raise Forbidden()
        card_date = card_service.patch_card_date(
            current_member,
            card_date,
            card_date_schema.load(
                request.json,
                partial=True,
                instance=card_date,
                session=db.session
            )
        )
        db.session.commit()
        return card_date_schema.dump(card_date)

    def delete(self, date_id: int):
        card_date: CardDate = CardDate.get_or_404(date_id)
        current_member = BoardAllowedUser.get_by_user_id(
            card_date.board_id, current_user.id
        )

        if not current_member:
            raise Forbidden()

        card_service.delete_card_date(current_member, card_date)
        db.session.commit()
        return {}


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
