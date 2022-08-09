from typing import List
from api.model.board import Board, BoardAllowedUser
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
    # User own boards
    boards = current_user.boards
    # Have acces to boards
    access_boards = BoardAllowedUser.query.filter(
        BoardAllowedUser.user_id == current_user.id)
    for board in access_boards:
        boards.append(board)
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
