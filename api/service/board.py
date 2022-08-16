from hashlib import new
from typing import List
import typing
import sqlalchemy as sqla

from api.model.board import Board, BoardAllowedUser, BoardRole
from api.model.list import BoardList
from api.app import db

from werkzeug.exceptions import Forbidden

from api.model.user import User


def get_user_boards(current_user: User) -> List[Board]:
    """Gets boards which available for user.

    Args:
        current_user (User): Current logged in user

    Returns:
        List[Board]: List of boards.
    """
    # Have acces to boards
    boards = []
    for entry in BoardAllowedUser.query.filter(
        BoardAllowedUser.user_id == current_user.id
    ).all():
        boards.append(entry.board)
    return boards


def get_board(current_user: User, board_id: int = None) -> Board:
    board = Board.get_or_404(board_id)
    if (
        board.is_user_can_access(current_user.id) or
        current_user.has_role("admin")
    ):
        return board
    raise Forbidden()


def post_board(current_user: User, data: dict) -> Board:
    """Creates a new board

    Args:
        current_user (User): Current logged in user
        data (dict): Data to add

    Returns:
        Board: Board ORM object
    """
    board = Board(owner_id=current_user.id, **data)
    return board


def patch_board(current_user: User, board: Board, data: dict) -> Board:
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
    if board.owner_id == current_user.id or current_user.has_role("admin"):
        board.update(**data)
        return board
    raise Forbidden()


def delete_board(current_user: User, board: Board):
    """Deletes a board.

    Args:
        current_user (User): Current logged in user
        board (Board): Board ORM object to delete

    Raises:
        Forbidden: User has no access to this board
    """
    if board.owner_id == current_user.id or current_user.has_role("admin"):
        db.session.delete(board)
    else:
        raise Forbidden()


def update_boardlists_position(
    current_user: User, board: Board, data: typing.List[int]
):
    if (
        board.is_user_can_access(current_user.id) or
        current_user.has_role("admin")
    ):
        for index, item in enumerate(data):
            db.session.query(BoardList).filter(
                sqla.and_(
                    BoardList.id == item,
                    BoardList.board_id == board.id
                )
            ).update({"position": index})


def get_board_claims(current_user: User, board: Board) -> BoardAllowedUser:
    """Gets board claims for current_user

    Args:
        current_user (User): Current logged in user
        board (Board): Board ORM object

    Returns:
        BoardAllowedUser: Board allowed user object contains role/permission.
    """
    return BoardAllowedUser.query.filter(
        sqla.and_(
            BoardAllowedUser.board_id == board.id,
            BoardAllowedUser.user_id == current_user.id,
        )
    ).first()


def get_board_roles(
    current_user: User, board: Board
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
    board_user = board.get_board_user(current_user.id)
    if (board_user or current_user.has_role("admin")):
        return board.board_roles
    raise Forbidden()


def add_member(
    current_user: User, board: Board,
    new_member: User, new_member_role: BoardRole
) -> BoardAllowedUser:
    """Adds member to board

    Args:
        current_user (User): current logged in user
        board (Board): Board to assign new member
        new_member (User): New member User object
        new_member_role (BoardRole): New member role.

    Raises:
        Forbidden: _description_

    Returns:
        BoardAllowedUser: _description_
    """
    board_user = board.get_board_user(current_user.id)
    if not board_user.role.is_admin:
        raise Forbidden()
    member = BoardAllowedUser(
        user_id=new_member.id,
        board_role_id=new_member_role.id,
    )
    board.board_users.append(member)
    return member


def remove_member(current_user: User, member: BoardAllowedUser):
    board_user = member.board.get_board_user(current_user.id)
    if not board_user.role.is_admin:
        raise Forbidden()
    db.session.delete(member)
