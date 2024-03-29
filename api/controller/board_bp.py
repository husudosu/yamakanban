
from werkzeug.exceptions import Forbidden

from flask import Blueprint, request, abort, jsonify
from flask.views import MethodView
from flask_jwt_extended import current_user, jwt_required
from webargs.flaskparser import use_args

from api.service.board import board_service, member_man_service
from api.util.dto import BoardDTO, CardDTO

board_bp = Blueprint("board_bp", __name__)


class BoardsAPI(MethodView):
    decorators = [jwt_required()]

    @use_args(BoardDTO.board_query_schema, location="query")
    def get(self, args: dict):
        return jsonify(BoardDTO.boards_schema.dump(
            board_service.get_user_boards(current_user, args),
            many=True
        ))

    def post(self):
        return BoardDTO.board_schema.dump(
            board_service.post(
                current_user,
                BoardDTO.board_schema.load(request.json)
            )
        )


class BoardAPI(MethodView):
    decorators = [jwt_required()]

    def get(self, board_id: int):
        return BoardDTO.board_schema.dump(
            board_service.get(current_user, board_id)
        )

    def patch(self, board_id: int):
        return BoardDTO.board_schema.dump(
            board_service.patch(
                current_user,
                board_id,
                BoardDTO.board_schema.load(request.json)
            )
        )

    def delete(self, board_id: int):
        board_service.delete(current_user, board_id)
        return {"message": "Board deleted"}


class RevertBoardAPI(MethodView):
    decorators = [jwt_required()]

    def post(self, board_id: int):
        """
        Reverts board.
        """
        return BoardDTO.board_schema.dump(
            board_service.revert(current_user, board_id)
        )


class BoardListsOrderAPI(MethodView):
    decorators = [jwt_required()]

    def patch(self, board_id: int):
        board_service.update_boardlists_position(
            current_user,
            board_id,
            request.json
        )
        return {}


class BoardUserClaimsAPI(MethodView):
    decorators = [jwt_required()]

    def get(self, board_id: int):
        claims = member_man_service.get_board_claims(
            current_user,
            board_id
        )
        if not claims:
            raise Forbidden()
        return BoardDTO.allowed_user_schema.dump(claims)


class BoardRolesAPI(MethodView):
    decorators = [jwt_required()]

    def get(self, board_id: int):
        return jsonify(BoardDTO.roles_schema.dump(
            member_man_service.get_board_roles(
                current_user,
                board_id
            ),
            many=True
        ))


class BoardFindMemberAPI(MethodView):
    decorators = [jwt_required()]

    def post(self, board_id: int):
        member = member_man_service.get_member(
            current_user,
            board_id,
            request.json["user_id"]
        )
        if not member:
            abort(404, "Member not found")
        return BoardDTO.allowed_user_schema.dump(member)


class BoardMemberAPI(MethodView):
    decorators = [jwt_required()]

    def get(self, board_id: int):
        return jsonify(BoardDTO.allowed_users_schema.dump(
            member_man_service.get_members(
                current_user,
                board_id
            ),
            many=True
        ))

    def post(self, board_id: int):
        return BoardDTO.allowed_user_schema.dump(member_man_service.add_member(
            current_user,
            board_id,
            request.json["user_id"],
            request.json["board_role_id"]
        ))

    def patch(self, board_id: int, user_id: int):
        return BoardDTO.allowed_user_schema.dump(
            member_man_service.update_member_role(
                current_user,
                board_id,
                user_id,
                request.json["board_role_id"]
            )
        )

    def delete(self, board_id: int, user_id: int):
        member_man_service.remove_member(board_id, current_user, user_id)
        return {"message": "Revoked access for user."}


class BoardMemberActivateAPI(MethodView):
    decorators = [jwt_required()]

    def post(self, member_id: int):
        member_man_service.activate_member(current_user, member_id)
        return {}


class BoardActvityAPI(MethodView):
    decorators = [jwt_required(), use_args(
        CardDTO.activity_schema_query, location="query")]

    def get(self, args, board_id: int):
        """
        Gets BoardActvity.
        """
        return CardDTO.activity_paginated_schema.dump(
            board_service.get_board_activities(current_user, board_id, args)
        )


class ArchivedListsAPI(MethodView):
    decorators = [jwt_required()]

    def get(self, board_id: int):
        """
        Gets ArchivedEntities.
        """
        return jsonify(BoardDTO.archived_lists_schema.dump(
            board_service.get_archived_lists(
                current_user, board_id
            ), many=True))


class ArchivedCardsAPI(MethodView):
    decorators = [jwt_required()]

    def get(self, board_id: int):
        """
        Gets ArchivedCards.
        """
        return jsonify(BoardDTO.archived_cards_schema.dump(
            board_service.get_archived_cards(
                current_user, board_id,
            ), many=True))


boards_view = BoardsAPI.as_view("boards-view")
board_view = BoardAPI.as_view("board-view")
revertboard_view = RevertBoardAPI.as_view("revertboard-view")
board_list_order_view = BoardListsOrderAPI.as_view("board-list-order-view")
board_user_claims_view = BoardUserClaimsAPI.as_view("board-user-claims-view")
board_roles_view = BoardRolesAPI.as_view("board-roles-views")
board_find_member_view = BoardFindMemberAPI.as_view("board-find-member-view")
board_member_view = BoardMemberAPI.as_view("board-member-view")
board_member_activate_view = BoardMemberActivateAPI.as_view(
    "board-member-activate-view")
board_actvitiy_view = BoardActvityAPI.as_view("boardactvity-view")

archivedlists_view = ArchivedListsAPI.as_view("archivedlists-view")
archivedcards_view = ArchivedCardsAPI.as_view("archivedcards-view")

board_bp.add_url_rule("/board", methods=["GET", "POST"], view_func=boards_view)
board_bp.add_url_rule("/board/<board_id>/revert",
                      methods=["POST"], view_func=revertboard_view)

board_bp.add_url_rule("/board/<board_id>",
                      methods=["GET", "PATCH", "DELETE"], view_func=board_view)

board_bp.add_url_rule("/board/<board_id>/boardlists-order",
                      methods=["PATCH"], view_func=board_list_order_view)

board_bp.add_url_rule("/board/<board_id>/user-claims",
                      methods=["GET"], view_func=board_user_claims_view)

# TODO: Later on we gonna add custom role support.
board_bp.add_url_rule("/board/<board_id>/roles",
                      methods=["GET"], view_func=board_roles_view)

board_bp.add_url_rule("/board/<board_id>/find-member",
                      methods=["POST"], view_func=board_find_member_view)

board_bp.add_url_rule("/board/<board_id>/member",
                      methods=["GET", "POST"], view_func=board_member_view)
board_bp.add_url_rule("/board/<board_id>/member/<user_id>",
                      methods=["PATCH", "DELETE"], view_func=board_member_view)

board_bp.add_url_rule("/board/member/<member_id>/activate",
                      methods=["POST"], view_func=board_member_activate_view)
board_bp.add_url_rule("/board/<board_id>/activities",
                      methods=["GET"], view_func=board_actvitiy_view)
board_bp.add_url_rule("/board/<board_id>/archived-lists",
                      view_func=archivedlists_view, methods=["GET"])
board_bp.add_url_rule("/board/<board_id>/archived-cards",
                      view_func=archivedcards_view, methods=["GET"])
