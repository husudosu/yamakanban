
from werkzeug.exceptions import Forbidden

from flask import Blueprint, request, jsonify, abort
from flask.views import MethodView
from flask_jwt_extended import current_user, jwt_required

from api.model.board import Board, BoardAllowedUser, BoardRole
from api.model.user import User
from api.service import board as board_service
from api.util.schemas import (
    BoardAllowedUserSchema, BoardRoleSchema, BoardSchema
)

from api.app import db, socketio

board_bp = Blueprint("board_bp", __name__)

board_schema = BoardSchema()
boards_schema = BoardSchema(exclude=("lists",))
board_allowed_user_schema = BoardAllowedUserSchema()
board_allowed_users_schema = BoardAllowedUserSchema(
    exclude=("role.permissions",))
board_roles_schema = BoardRoleSchema()


class BoardAPI(MethodView):
    decorators = [jwt_required()]

    def get(self, board_id: int = None):
        # Get single board
        if board_id:
            return board_schema.dump(
                board_service.get_board(current_user, board_id)
            )

        # Get all boards accessable for user
        return jsonify(boards_schema.dump(
            board_service.get_user_boards(current_user),
            many=True,
        ))

    def post(self):
        board = board_service.post_board(
            current_user,
            board_schema.load(request.json)
        )
        db.session.add(board)
        db.session.commit()
        db.session.refresh(board)
        return board_schema.dump(board)

    def patch(self, board_id: int):
        updated_board = board_service.patch_board(
            current_user,
            Board.get_or_404(board_id),
            board_schema.load(request.json)
        )
        db.session.commit()
        db.session.refresh(updated_board)
        return board_schema.dump(updated_board)

    def delete(self, board_id: int):
        board_service.delete_board(current_user, Board.get_or_404(board_id))
        db.session.commit()
        return {}


class BoardListsOrderAPI(MethodView):
    decorators = [jwt_required()]

    def patch(self, board_id: int):
        board_service.update_boardlists_position(
            current_user,
            Board.get_or_404(board_id),
            request.json
        )
        db.session.commit()
        socketio.emit(
            "list.update.order",
            request.json,
            namespace="/board",
            to=f"board-{board_id}"
        )
        return {}


class BoardUserClaimsAPI(MethodView):
    decorators = [jwt_required()]

    def get(self, board_id: int):
        claims = board_service.get_board_claims(
            current_user,
            Board.get_or_404(board_id)
        )
        if not claims:
            raise Forbidden()
        return board_allowed_user_schema.dump(claims)


class BoardRolesAPI(MethodView):
    decorators = [jwt_required()]

    def get(self, board_id: int):
        return jsonify(board_roles_schema.dump(
            board_service.get_board_roles(
                current_user,
                Board.get_or_404(board_id)
            ),
            many=True
        ))


class BoardFindMemberAPI(MethodView):
    decorators = [jwt_required()]

    def post(self, board_id: int):
        member = board_service.get_member(
            current_user,
            Board.get_or_404(board_id),
            request.json["user_id"]
        )
        if not member:
            abort(404, "Member not found.")
        return board_allowed_user_schema.dump(member)


class BoardMemberAPI(MethodView):
    decorators = [jwt_required()]

    def get(self, board_id: int):
        return jsonify(board_allowed_users_schema.dump(
            board_service.get_members(
                current_user,
                Board.get_or_404(board_id)
            ),
            many=True
        ))

    def post(self, board_id: int):
        data = board_allowed_user_schema.load(request.json)
        member = board_service.add_member(
            current_user,
            Board.get_or_404(board_id),
            User.get_or_404(data["user_id"]),
            BoardRole.get_board_role_or_404(board_id, data["board_role_id"])
        )
        db.session.commit()
        return board_allowed_user_schema.dump(member)

    def patch(self, board_id: int, user_id: int):
        # TODO: Create marshmallow schema for loading data!
        member = board_service.update_member_role(
            current_user,
            Board.get_or_404(board_id),
            User.get_or_404(user_id),
            BoardRole.get_board_role_or_404(
                board_id, request.json["board_role_id"])
        )
        db.session.commit()
        db.session.refresh(member)
        return board_allowed_user_schema.dump(member)

    def delete(self, board_id: int, user_id: int):
        board = Board.get_or_404(board_id)
        current_member = BoardAllowedUser.get_by_user_id(
            board.id, current_user.id)

        if not current_member:
            abort(403)
        member = BoardAllowedUser.get_by_user_id(board.id, user_id)

        if not member:
            abort(404)

        board_service.remove_member(
            current_member,
            member
        )
        db.session.commit()
        return {}


class BoardMemberActivateAPI(MethodView):
    decorators = [jwt_required()]

    def post(self, member_id: int):
        member_to_activate = BoardAllowedUser.get_or_404(member_id)
        member = BoardAllowedUser.get_by_user_id(
            member_to_activate.board_id, current_user.id)

        if not member:
            raise Forbidden()

        board_service.activate_member(member, member_to_activate)
        db.session.commit()
        return {}


board_view = BoardAPI.as_view("board-view")
board_list_order_view = BoardListsOrderAPI.as_view("board-list-order-view")
board_user_claims_view = BoardUserClaimsAPI.as_view("board-user-claims-view")
board_roles_view = BoardRolesAPI.as_view("board-roles-views")
board_find_member_view = BoardFindMemberAPI.as_view("board-find-member-view")
board_member_view = BoardMemberAPI.as_view("board-member-view")
board_member_activate_view = BoardMemberActivateAPI.as_view(
    "board-member-activate-view")


board_bp.add_url_rule("/board", methods=["GET", "POST"], view_func=board_view)
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
