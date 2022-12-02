import typing
from werkzeug.exceptions import Forbidden

from api.app import db, socketio
from api.model import BoardPermission
from api.model.user import User
from api.model.board import BoardAllowedUser, Board
from api.model.list import BoardList
from api.model.card import Card
from api.socket import SIOEvent

from api.util.dto import ListDTO
import sqlalchemy as sqla


class ListService:

    def get(self, current_user: User, board_id: int) -> typing.List[BoardList]:
        board = Board.get_or_404(board_id)
        BoardAllowedUser.get_by_usr_or_403(
            board_id, current_user.id)
        return board.lists

    def post(self, current_user: User, board_id: int, data: dict) -> BoardList:
        board = Board.get_or_404(board_id)
        current_member = BoardAllowedUser.get_by_usr_or_403(
            board_id, current_user.id)
        if current_member.has_permission(BoardPermission.LIST_CREATE):
            # TODO Add activity log entry too!
            position_max = db.engine.execute(
                f"SELECT MAX(position) FROM list WHERE board_id={board.id}"
            ).fetchone()

            boardlist = BoardList(**data)
            if position_max[0] is not None:
                boardlist.position = position_max[0] + 1
            board.lists.append(boardlist)

            db.session.add(boardlist)
            db.session.commit()
            db.session.refresh(boardlist)

            socketio.emit(
                SIOEvent.LIST_NEW.value,
                ListDTO.lists_schema.dump(boardlist),
                namespace="/board",
                to=f"board-{boardlist.board_id}"
            )

            return boardlist
        raise Forbidden()

    def patch(self, current_user: User, list_id: int, data: dict) -> BoardList:
        board_list = BoardList.get_or_404(list_id)
        current_member = BoardAllowedUser.get_by_usr_or_403(
            board_list.board_id, current_user.id)
        if current_member.has_permission(BoardPermission.LIST_EDIT):
            # TODO Add activity log entry too!
            board_list.update(**data)
            db.session.commit()
            db.session.refresh(board_list)

            socketio.emit(
                SIOEvent.LIST_UPDATE.value,
                ListDTO.update_list_schema.dump(board_list),
                namespace="/board",
                to=f"board-{board_list.board_id}"
            )
            return board_list
        raise Forbidden()

    def delete(self, current_user: User, list_id: int):
        board_list = BoardList.get_or_404(list_id)
        current_member = BoardAllowedUser.get_by_usr_or_403(
            board_list.board_id, current_user.id)
        if current_member.has_permission(BoardPermission.LIST_DELETE):
            dmp = ListDTO.lists_schema.dump(board_list)
            db.session.delete(board_list)
            db.session.commit()

            # TODO: This can be converted to entity_id based event.
            socketio.emit(
                SIOEvent.LIST_DELETE.value,
                dmp,
                namespace="/board",
                to=f"board-{board_list.board_id}"
            )
        else:
            raise Forbidden()

    def update_cards_position(self, current_user: User, list_id: int, data: typing.List[int]):
        board_list = BoardList.get_or_404(list_id)
        current_member = BoardAllowedUser.get_by_usr_or_403(
            board_list.board_id, current_user.id)
        if current_member.has_permission(BoardPermission.LIST_EDIT):
            for index, item in enumerate(data):
                db.session.query(Card).filter(
                    sqla.and_(Card.id == item, Card.list_id == board_list.id)
                ).update({"position": index})
            db.session.commit()

            socketio.emit(
                SIOEvent.CARD_UPDATE_ORDER.value,
                {"order": data, "list_id": board_list.id},
                namespace="/board",
                to=f"board-{board_list.board_id}"
            )


list_service = ListService()
