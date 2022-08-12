import typing
from werkzeug.exceptions import Forbidden
import sqlalchemy as sqla


from api.app import db
from api.model.card import Card, CardListChange
from api.model.user import User
from api.model.list import BoardList
from api.model.board import Board


def get_board_lists(
    current_user: User, board: Board
) -> typing.List[BoardList]:
    if (
        board.is_user_can_access(current_user.id) or
        current_user.has_role("admin")
    ):
        return board.lists
    raise Forbidden()


def post_board_list(current_user: User, board: Board, data: dict) -> BoardList:
    # TODO: Add board permission checking too!
    if (
        board.is_user_can_access(current_user.id) or
        current_user.has_role("admin")
    ):
        # TODO Add activity log entry too!
        boardlist = BoardList(**data)
        board.lists.append(boardlist)
        db.session.add(board)
        return boardlist
    raise Forbidden()


def patch_board_list(
    current_user: User, board_list: BoardList, data: dict
) -> BoardList:
    # TODO: Add board permission checking too!
    if (
        board_list.board.is_user_can_access(current_user.id) or
        current_user.has_role("admin")
    ):
        # TODO Add activity log entry too!
        board_list.update(**data)
        return board_list
    raise Forbidden()


def delete_board_list(current_user: User, board_list: BoardList):
    # TODO: Add board permission checking too!
    if (
        board_list.board.is_user_can_access(current_user.id) or
        current_user.has_role("admin")
    ):
        # Make CardListChange event from_list_id, to_list_id to null
        db.session.query(CardListChange).filter(
            CardListChange.from_list_id == board_list.id
        ).update({"from_list_id": None})
        db.session.query(CardListChange).filter(
            CardListChange.to_list_id == board_list.id
        ).update({"to_list_id": None})

        db.session.delete(board_list)
    else:
        raise Forbidden()


def update_cards_position(
    current_user: User, board_list: BoardList, data: typing.List[int]
):
    if (
        board_list.board.is_user_can_access(current_user.id) or
        current_user.has_role("admin")
    ):
        for index, item in enumerate(data):
            db.session.query(Card).filter(
                sqla.and_(Card.id == item, Card.list_id == board_list.id)
            ).update({"position": index})
