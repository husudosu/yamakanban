from typing import List
import typing
import sqlalchemy as sqla
import sqlalchemy.orm as sqla_orm

from api.model.board import Board, BoardAllowedUser, BoardRole
from api.model.list import BoardList
from api.model import BoardPermission
from api.app import db, socketio
from api.socket import SIOEvent

from werkzeug.exceptions import Forbidden
from marshmallow.exceptions import ValidationError

from api.model.user import User


class BoardService:

    def get_user_boards(self, current_user: User) -> List[Board]:
        """Gets boards which available for user.

        Args:
            current_user (User): Current logged in user

        Returns:
            List[Board]: List of boards.
        """
        return [
            entry.board for entry in BoardAllowedUser.query.filter(
                sqla.and_(
                    BoardAllowedUser.user_id == current_user.id,
                    BoardAllowedUser.is_deleted == False
                )
            ).options(sqla_orm.load_only(BoardAllowedUser.id)).all()
        ]

    def get(self, current_user: User, board_id: int = None) -> Board:
        board = Board.get_or_404(board_id)
        if board.is_user_can_access(current_user.id):
            return board
        raise Forbidden()

    def post_board(self, current_user: User, data: dict) -> Board:
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
        return board

    def patch_board(self, current_user: User, board_id: int, data: dict) -> Board:
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
            db.session.refresh(board)
            return board
        raise Forbidden()

    def delete_board(self, current_user: User, board_id: int):
        """Deletes a board.

        Args:
            current_user (User): Current logged in user
            board (Board): Board ORM object to delete

        Raises:
            Forbidden: User has no access to this board
        """

        # Only allow deletion for owner
        board = Board.get_or_404(board_id)

        if board.owner_id == current_user.id:
            db.session.delete(board)
            db.session.commit()
        else:
            raise Forbidden()

    def update_boardlists_position(
        self, current_user: User, board_id: int, data: typing.List[int]
    ):
        board = Board.get_or_404(board_id)
        BoardAllowedUser.get_by_usr_or_403(board_id, current_user.id)

        if board.is_user_can_access(current_user.id):
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
        """Gets board member if exists.

        Args:
            current_user (User): Current logged in user
            board (Board): Board
            user_id (int): User ID which we want to get board user.

        Raises:
            Forbidden: Don't have permission to access the board

        Returns:
            typing.Union[BoardAllowedUser, None]: Board user or None if not exists.
        """
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
        board = Board.get_or_404(board_id)
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
        member.role = role

        db.session.commit()
        db.session.refresh(member)
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
            # TODO We should raise not found.
            pass
        if current_member.id == member.id:
            raise ValidationError({"user_id": ["You can't remove yourself."]})

        if not member.is_deleted:
            # If the user not soft deleted yet, do a soft delete.
            member.is_deleted = True
            db.session.commit()
        else:
            db.session.delete(member)
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
        db.session.commit()


board_service = BoardService()
