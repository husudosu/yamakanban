import os
import shutil

from typing import List
from datetime import datetime
from flask import current_app
import json
import typing
import sqlalchemy as sqla
import sqlalchemy.orm as sqla_orm

from werkzeug.exceptions import Forbidden, NotFound
from marshmallow.exceptions import ValidationError

from api.model.board import Board, BoardAllowedUser, BoardRole
from api.model.card import Card, BoardActivity
from api.model.list import BoardList

from api.model import BoardPermission, BoardActivityEvent
from api.app import db, socketio
from api.socket import SIOEvent
from api.model.user import User
from api.util.dto import BoardDTO


class BoardService:

    def get_user_boards(self, current_user: User, args: dict) -> List[Board]:
        """Gets accessible non-archived user boards. 

        Args:
            current_user (User): _description_

        Returns:
            List[Board]: _description_
        """
        return [
            entry.board for entry in BoardAllowedUser.query.filter(
                sqla.and_(
                    BoardAllowedUser.user_id == current_user.id,
                    BoardAllowedUser.is_deleted == False,
                    BoardAllowedUser.board.has(
                        Board.archived == args["archived"])
                )
            ).options(sqla_orm.load_only(BoardAllowedUser.id)).all()
        ]

    def get(self, current_user: User, board_id: int = None) -> Board:
        board = Board.get_or_404(board_id)
        BoardAllowedUser.get_by_usr_or_403(board_id, current_user.id)

        # Get non archived lists first
        board.lists = BoardList.query.filter(
            sqla.and_(
                BoardList.board_id == board.id,
                BoardList.archived == False
            )
        ).order_by(BoardList.position.asc()).all()

        # Get not archived list card
        for li in board.lists:
            li.cards = Card.query.filter(
                sqla.and_(
                    Card.list_id == li.id,
                    Card.archived == False
                )
            ).order_by(Card.position.asc()).all()
        return board

    def get_board_activities(self, current_user: User, board_id: int, args: dict):
        # TODO: This is almost full duplicate of Card service->get_activities method. Need refactor here!
        Board.get_or_404(board_id)
        BoardAllowedUser.get_by_usr_or_403(board_id, current_user.id)

        query = BoardActivity.query.filter(BoardActivity.board_id == board_id)

        # Get between two dates
        if "dt_from" in args.keys() and "dt_to" in args.keys():
            query = query.filter(
                BoardActivity.activity_on.between(
                    args["dt_from"],
                    args["dt_to"]
                )
            )
        elif "dt_from" in args.keys():
            query = query.filter(
                BoardActivity.activity_on >= args["dt_from"]
            )
        elif "dt_to" in args.keys():
            query = query.filter(
                BoardActivity.activity_on < args["dt_to"]
            )

        # Filter by user id
        if "board_user_id" in args.keys():
            query = query.filter(
                BoardActivity.board_user_id == args["board_user_id"]
            )

        # Sortby
        sortby = args.get("sort_by", "activity_on")
        order = args.get("order", "desc")

        if not hasattr(BoardActivity, sortby):
            sortby = "activity_on"

        if order == "asc":
            query = query.order_by(sqla.asc(getattr(BoardActivity, sortby)))
        elif order == "desc":
            query = query.order_by(sqla.desc(getattr(BoardActivity, sortby)))

        return query.paginate(args["page"], args["per_page"])

    def get_archived_entitities(self, current_user: User, board_id: int, args: dict):
        entity_type = args.get("entity_type")
        Board.get_or_404(board_id)
        BoardAllowedUser.get_by_usr_or_403(board_id, current_user.id)
        match entity_type:
            case "card":
                return Card.query.filter(
                    sqla.and_(
                        Card.board_id == board_id,
                        sqla.or_(
                            Card.archived == True,
                            Card.archived_by_list == True
                        )
                    )
                ).order_by(Card.archived_on.desc()).all()
            case "list":
                return BoardList.query.filter(
                    sqla.and_(
                        BoardList.board_id == board_id,
                        BoardList.archived == True
                    )
                ).options(
                    sqla_orm.joinedload(BoardList.cards)
                ).order_by(BoardList.archived_on.desc()).all()

    def post(self, current_user: User, data: dict) -> Board:
        """Creates a new board

        Args:
            current_user (User): Current logged in user
            data (dict): Data to add

        Returns:
            Board: Board ORM object
        """
        board = Board(owner_id=current_user.id, **data)
        db.session.add(board)
        db.session.commit()
        # Create Board activity
        current_member = BoardAllowedUser.get_by_usr_or_403(
            board.id, current_user.id)
        board.activities.append(
            BoardActivity(
                board_user_id=current_member.id,
                event=BoardActivityEvent.BOARD_CREATE.value,
            )
        )
        db.session.commit()
        return board

    def patch(self, current_user: User, board_id: int, data: dict) -> Board:
        """Updates a board.

        Args:
            current_user (User): Current logged in user
            board (Board): Board ORM object to update
            data (dict): update data

        Raises:
            Forbidden: User has no access to this board

        Returns:
            Board: Updated board ORM object
        """
        board = Board.get_or_404(board_id)
        current_member: BoardAllowedUser = BoardAllowedUser.get_by_usr_or_403(
            board.id, current_user.id)
        if board.owner_id == current_user.id or current_member.has_permission(BoardPermission.BOARD_EDIT):
            board.update(**data)
            db.session.commit()
            socketio.emit(
                SIOEvent.BOARD_UPDATE.value,
                BoardDTO.board_schema.dump(board),
                namespace="/board",
                to=f"board-{board.id}"
            )
            return board
        raise Forbidden()

    def delete(self, current_user: User, board_id: int):
        """First archives the board. For the second time deletes board from db.

        Args:
            current_user (User): Current user
            board_id (int): Board id to archive/delete
        """
        # Only allow deletion for owner
        board: Board = Board.get_or_404(board_id)
        current_member = BoardAllowedUser.get_by_usr_or_403(
            board_id, current_user.id)

        # Board owner id is User.id not BoardAllowedUser.id!
        if board.owner_id == current_user.id:
            if not board.archived:
                board.archived = True
                board.archived_on = datetime.utcnow()

                # Create activity
                board.activities.append(
                    BoardActivity(
                        board_user_id=current_member.id,
                        event=BoardActivityEvent.BOARD_ARCHIVE.value,
                    )
                )
                db.session.commit()
                socketio.emit(
                    SIOEvent.BOARD_UPDATE.value,
                    BoardDTO.board_schema.dump(board),
                    namespace="/board",
                    to=f"board-{board.id}"
                )
            else:
                # We delete files for board
                upload_path = os.path.join(
                    current_app.config["USER_UPLOAD_DIR"],
                    str(board.id)
                )

                if os.path.exists(upload_path):
                    shutil.rmtree(upload_path)

                db.session.delete(board)
                db.session.commit()
                socketio.emit(
                    SIOEvent.BOARD_DELETE.value,
                    board_id,
                    namespace="/board",
                    to=f"board-{board_id}"
                )
        else:
            raise Forbidden()

    def revert(self, current_user: User, board_id: int):
        board: Board = Board.get_or_404(board_id)
        current_member = BoardAllowedUser.get_by_usr_or_403(
            board_id, current_user.id)
        if board.owner_id == current_user.id:
            if board.archived:
                board.archived = False
                board.archived_on = None

                # Create activity
                board.activities.append(
                    BoardActivity(
                        board_user_id=current_member.id,
                        event=BoardActivityEvent.BOARD_REVERT.value,
                    )
                )
                db.session.commit()
                socketio.emit(
                    SIOEvent.BOARD_UPDATE.value,
                    BoardDTO.board_schema.dump(board),
                    namespace="/board",
                    to=f"board-{board.id}"
                )
                return board
        else:
            raise Forbidden()

    def update_boardlists_position(
        self, current_user: User, board_id: int, data: typing.List[int]
    ):
        board = Board.get_or_404(board_id)
        BoardAllowedUser.get_by_usr_or_403(board_id, current_user.id)

        for index, item in enumerate(data):
            db.session.query(BoardList).filter(
                sqla.and_(
                    BoardList.id == item,
                    BoardList.board_id == board.id
                )
            ).update({"position": index})
        db.session.commit()
        socketio.emit(
            SIOEvent.LIST_UPDATE_ORDER.value,
            data,
            namespace="/board",
            to=f"board-{board_id}"
        )

    def get_board_claims(self, current_user: User, board_id: int) -> BoardAllowedUser:
        """Gets board claims for current_user

        Args:
            current_user (User): Current logged in user
            board (Board): Board ORM object

        Returns:
            BoardAllowedUser: Board allowed user object contains role/permission.
        """
        BoardAllowedUser.get_by_usr_or_403(board_id, current_user.id)
        return BoardAllowedUser.query.filter(
            sqla.and_(
                BoardAllowedUser.board_id == board_id,
                BoardAllowedUser.user_id == current_user.id,
            )
        ).first()

    def get_board_roles(
        self, current_user: User, board_id: int
    ) -> typing.List[BoardRole]:
        """Gets board roles

        Args:
            current_user (User): Current logged in user
            board (Board): Board

        Raises:
            Forbidden: _description_

        Returns:
            typing.List[BoardRole]: _description_
        """
        board = Board.get_or_404(board_id)
        BoardAllowedUser.get_by_usr_or_403(
            board_id, current_user.id)
        return board.board_roles

    def get_member(
        self, current_user: User, board_id: int, user_id: int
    ) -> typing.Union[BoardAllowedUser, None]:
        board = Board.get_or_404(board_id)
        BoardAllowedUser.get_by_usr_or_403(board_id, current_user.id)
        return board.get_board_user(user_id)

    def get_members(
        self, current_user: User, board_id: int
    ) -> typing.List[BoardAllowedUser]:
        board = Board.get_or_404(board_id)
        BoardAllowedUser.get_by_usr_or_403(board.id, current_user.id)
        return board.board_users

    def add_member(
        self, current_user: User, board_id: int,
        new_user_id: int, new_member_role_id: int
    ) -> BoardAllowedUser:
        board: Board = Board.get_or_404(board_id)
        current_member = BoardAllowedUser.get_by_usr_or_403(
            board_id, current_user.id)

        if not current_member.role.is_admin:
            raise Forbidden()

        # Check if user already exists
        if BoardAllowedUser.query.filter(
            sqla.and_(
                BoardAllowedUser.user_id == new_user_id,
                BoardAllowedUser.board_id == board.id
            )
        ).first():
            raise ValidationError(
                {"user_id": ["User already member on board."]})

        member = BoardAllowedUser(
            user_id=User.get_or_404(new_user_id).id,
            board_role_id=BoardRole.get_board_role_or_404(
                board.id, new_member_role_id).id,
        )
        board.board_users.append(member)
        db.session.commit()

        board.activities.append(
            BoardActivity(
                board_user_id=current_member.id,
                event=BoardActivityEvent.MEMBER_ADD.value,
                changes=json.dumps(
                    {
                        "to":
                            {
                                "member_user_name": member.user.name,
                                "member_role_name": member.role.name
                            }
                    }
                )
            )
        )
        db.session.commit()
        return member

    def update_member_role(
        self, current_user: User, board_id: int,
        user_id: int, role_id: int
    ):
        board = Board.get_or_404(board_id)
        current_member = BoardAllowedUser.get_by_usr_or_403(
            board_id, current_user.id)
        user = User.get_or_404(user_id)
        role = BoardRole.get_board_role_or_404(board_id, role_id)

        # You can't modify your own role.
        if current_member.user_id == user.id:
            raise ValidationError(
                {"user_id": ["You can't update your own role."]})

        if not current_member.role.is_admin:
            raise Forbidden()

        member = board.get_board_user(user.id)
        old_member_role_name = member.role.name
        member.role = role

        db.session.commit()

        board.activities.append(
            BoardActivity(
                board_user_id=current_member.id,
                event=BoardActivityEvent.MEMBER_CHANGE_ROLE.value,
                changes=json.dumps(
                    {
                        "from": {
                            "member_user_name": member.user.name,
                            "member_role_name": old_member_role_name
                        },
                        "to": {
                            "member_user_name": member.user.name,
                            "member_role_name": member.role.name
                        }
                    }
                )
            )
        )
        db.session.commit()
        return member

    def remove_member(
        self, board_id: int, current_user: User, user_id: int
    ):
        board = Board.get_or_404(board_id)
        current_member = BoardAllowedUser.get_by_usr_or_403(
            board.id, current_user.id)

        if not current_member.role.is_admin:
            raise Forbidden()

        member = BoardAllowedUser.get_by_user_id(board_id, user_id)
        if not member:
            raise NotFound("Member not found")
        if current_member.id == member.id:
            raise ValidationError({"user_id": ["You can't remove yourself."]})

        if not member.is_deleted:
            # If the user not soft deleted yet, do a soft delete.
            member.is_deleted = True
            board.activities.append(
                BoardActivity(
                    board_user_id=current_member.id,
                    event=BoardActivityEvent.MEMBER_ACCESS_REVOKE.value,
                    changes=json.dumps(
                        {
                            "to": {
                                "member_user_name": member.user.name,
                            },
                        }
                    )
                )
            )
            db.session.commit()
        else:
            member_user_name = member.user.name
            db.session.delete(member)
            board.activities.append(
                BoardActivity(
                    board_user_id=current_member.id,
                    event=BoardActivityEvent.MEMBER_DELETE.value,
                    changes=json.dumps(
                        {
                            "to": {
                                "member_user_name": member_user_name,
                            },
                        }
                    )
                )
            )
            db.session.commit()

    def activate_member(
        self, current_user: User, member_id: int
    ):
        member = BoardAllowedUser.get_or_404(member_id)
        current_member = BoardAllowedUser.get_by_usr_or_403(
            member.board_id, current_user.id)
        if not current_member.role.is_admin:
            raise Forbidden()

        member.is_deleted = False
        current_member.board.activities.append(
            BoardActivity(
                board_user_id=current_member.id,
                event=BoardActivityEvent.MEMBER_REVERT.value,
                changes=json.dumps(
                    {
                        "to": {
                            "member_user_name": member.user.name,
                        },
                    }
                )
            )
        )
        db.session.commit()


board_service = BoardService()
