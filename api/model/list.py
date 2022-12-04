import sqlalchemy as sqla
import sqlalchemy.orm as sqla_orm

from api.app import db
from . import BaseMixin


class BoardList(db.Model, BaseMixin):
    __tablename__ = "list"

    id = sqla.Column(sqla.Integer, primary_key=True)
    board_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("board.id", ondelete="CASCADE"), nullable=False)
    title = sqla.Column(sqla.Text, nullable=False)
    position = sqla.Column(sqla.SmallInteger, default=0)

    archived = sqla.Column(sqla.Boolean, server_default="0", default=False)
    archived_on = sqla.Column(sqla.DateTime)

    board = sqla_orm.relationship("Board", back_populates="lists")
    cards = sqla_orm.relationship(
        "Card",
        back_populates="board_list",
        lazy="noload"
    )
