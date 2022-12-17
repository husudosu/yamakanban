import typing

import json
from datetime import datetime
from werkzeug.exceptions import Forbidden
from api.app import db, socketio
from api.model import BoardPermission, BoardActivityEvent
from api.model.user import User
from api.model.board import BoardAllowedUser, Board
from api.model.list import BoardList
from api.model.card import Card, BoardActivity
from api.socket import SIOEvent

from api.util.dto import ListDTO
import sqlalchemy as sqla


class ListService:

    def get(self, current_user: User, board_id: int) -> typing.List[BoardList]:
        board = Board.get_or_404(board_id)
        BoardAllowedUser.get_by_usr_or_403(
            board_id, current_user.id)

        # Load cards into lists.
        lists = []
        for li in board.lists:
            li.cards = Card.query.filter(
                sqla.and_(
                    Card.list_id == li.id,
                    Card.archived == False
                )
            ).order_by(Card.position.asc()).all()
        return lists

    def post(self, current_user: User, board_id: int, data: dict) -> BoardList:
        board: Board = Board.get_or_404(board_id)
        current_member = BoardAllowedUser.get_by_usr_or_403(
            board_id, current_user.id)
        if current_member.has_permission(BoardPermission.LIST_CREATE):
            position_max = db.engine.execute(
                f"SELECT MAX(position) FROM list WHERE board_id={board.id}"
            ).fetchone()

            boardlist = BoardList(**data)
            if position_max[0] is not None:
                boardlist.position = position_max[0] + 1
            board.lists.append(boardlist)

            board.activities.append(
                BoardActivity(
                    board_user_id=current_member.id,
                    event=BoardActivityEvent.LIST_CREATE.value,
                    entity_id=boardlist.id,
                    changes=json.dumps(
                        {
                            "to": {
                                "title": boardlist.title
                            }
                        }
                    )
                )
            )
            db.session.commit()

            socketio.emit(
                SIOEvent.LIST_NEW.value,
                ListDTO.lists_schema.dump(boardlist),
                namespace="/board",
                to=f"board-{boardlist.board_id}"
            )

            return boardlist
        raise Forbidden()

    def archive_list(self, current_member: BoardAllowedUser, board_list: BoardList):
        dmp = ListDTO.lists_schema.dump(board_list)
        board_list.board.activities.append(
            BoardActivity(
                board_user_id=current_member.id,
                event=BoardActivityEvent.LIST_ARCHIVE.value,
                entity_id=board_list.id,
                changes=json.dumps(
                    {
                        "to": {
                            "title": board_list.title
                        }
                    }
                )
            )
        )
        board_list.archived = True
        board_list.archived_on = datetime.utcnow()

        # Update archived state on cards
        db.session.query(Card).filter(
            sqla.and_(
                Card.list_id == board_list.id,
                Card.archived == False
            )
        ).update({"archived_by_list": True, "archived_on": datetime.utcnow()})

        db.session.commit()

        # Send deleted list event
        socketio.emit(
            SIOEvent.LIST_DELETE.value,
            dmp,
            namespace="/board",
            to=f"board-{board_list.board_id}"
        )

    def revert_list(self, current_member: BoardAllowedUser, board_list: BoardList):
        board_list.board.activities.append(
            BoardActivity(
                board_user_id=current_member.id,
                event=BoardActivityEvent.LIST_REVERT.value,
                entity_id=board_list.id,
                changes=json.dumps(
                    {
                        "to": {
                            "title": board_list.title
                        }
                    }
                )
            )
        )
        board_list.archived = False
        board_list.archived_on = None
        # Update archived state on cards
        db.session.query(Card).filter(
            sqla.and_(
                Card.list_id == board_list.id,
                Card.archived == False
            )
        ).update({"archived_by_list": False, "archived_on": None})
        db.session.commit()

        # Load cards into boardlist
        board_list.cards = Card.query.filter(
            sqla.and_(
                Card.list_id == board_list.id,
                Card.archived == False
            )
        ).all()

        # Dump list and send socket.io event
        dmp = ListDTO.lists_schema.dump(board_list)
        socketio.emit(
            SIOEvent.LIST_NEW.value,
            dmp,
            namespace="/board",
            to=f"board-{board_list.board_id}"
        )

    def patch(self, current_user: User, list_id: int, data: dict) -> BoardList:
        board_list = BoardList.get_or_404(list_id)
        current_member = BoardAllowedUser.get_by_usr_or_403(
            board_list.board_id, current_user.id)
        if current_member.has_permission(BoardPermission.LIST_EDIT):
            old_title = board_list.title

            if board_list.archived != data.get("archived", board_list.archived):
                if data["archived"]:
                    self.archive_list(current_member, board_list)
                else:
                    self.revert_list(current_member, board_list)

            board_list.update(**data)

            if old_title != board_list.title:
                board_list.board.activities.append(
                    BoardActivity(
                        board_user_id=current_member.id,
                        event=BoardActivityEvent.LIST_UPDATE.value,
                        entity_id=board_list.id,
                        changes=json.dumps(
                            {
                                "from": {
                                    "title": old_title
                                },
                                "to": {
                                    "title": board_list.title
                                }
                            }
                        )
                    )
                )
                db.session.commit()

                socketio.emit(
                    SIOEvent.LIST_UPDATE.value,
                    ListDTO.update_list_schema.dump(board_list),
                    namespace="/board",
                    to=f"board-{board_list.board_id}"
                )
            return board_list
        raise Forbidden()

    def delete(self, current_user: User, list_id: int):
        board_list: BoardList = BoardList.get_or_404(list_id)
        current_member = BoardAllowedUser.get_by_usr_or_403(
            board_list.board_id, current_user.id)
        if current_member.has_permission(BoardPermission.LIST_DELETE):
            dmp = ListDTO.lists_schema.dump(board_list)
            if not board_list.archived:
                self.archive_list(current_member, board_list)
            else:
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
