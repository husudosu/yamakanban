import typing
from werkzeug.exceptions import Forbidden
import sqlalchemy as sqla


from api.app import db
from api.model import BoardPermission
from api.model.card import Card
from api.model.user import User
from api.model.list import BoardList
from api.model.board import Board, BoardAllowedUser


def get_board_lists(
    current_user: User, board: Board
) -> typing.List[BoardList]:
    if (
        board.is_user_can_access(current_user.id) or
        current_user.has_role("admin")
    ):
        return board.lists
    raise Forbidden()


def post_board_list(current_member: BoardAllowedUser, board: Board, data: dict) -> BoardList:
    if current_member.has_permission(BoardPermission.LIST_CREATE):
        # TODO Add activity log entry too!
        position_max = db.engine.execute(
            f"SELECT MAX(position) FROM list WHERE board_id={board.id}"
        ).fetchone()

        boardlist = BoardList(**data)
        if position_max[0] is not None:
            boardlist.position = position_max[0] + 1
        board.lists.append(boardlist)
        return boardlist
    raise Forbidden()


def patch_board_list(
    current_member: BoardAllowedUser, board_list: BoardList, data: dict
) -> BoardList:
    if current_member.has_permission(BoardPermission.LIST_EDIT):
        # TODO Add activity log entry too!
        board_list.update(**data)
        return board_list
    raise Forbidden()


def delete_board_list(current_member: BoardAllowedUser, board_list: BoardList):
    if current_member.has_permission(BoardPermission.LIST_DELETE):
        db.session.delete(board_list)
    else:
        raise Forbidden()


def update_cards_position(
    current_member: BoardAllowedUser, board_list: BoardList, data: typing.List[int]
):
    if current_member.has_permission(BoardPermission.LIST_EDIT):
        for index, item in enumerate(data):
            db.session.query(Card).filter(
                sqla.and_(Card.id == item, Card.list_id == board_list.id)
            ).update({"position": index})
