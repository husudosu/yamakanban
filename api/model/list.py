import sqlalchemy as sqla
import sqlalchemy.orm as sqla_orm

from api.app import db
from . import BaseMixin
from api.model.card import Card


class BoardList(db.Model, BaseMixin):
    __tablename__ = "list"

    id = sqla.Column(sqla.Integer, primary_key=True)
    board_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("board.id", ondelete="CASCADE"), nullable=False)
    title = sqla.Column(sqla.Text, nullable=False)
    position = sqla.Column(sqla.SmallInteger, default=0)

    archived = sqla.Column(sqla.Boolean, server_default="0", default=False)
    archived_on = sqla.Column(sqla.DateTime)
    wip_limit = sqla.Column(sqla.Integer, nullable=False,
                            server_default="-1", default=0)

    header_bgcolor = sqla.Column(sqla.String)
    header_textcolor = sqla.Column(sqla.String)
    list_bgcolor = sqla.Column(sqla.String)
    list_textcolor = sqla.Column(sqla.String)

    board = sqla_orm.relationship("Board", back_populates="lists")
    cards = sqla_orm.relationship(
        "Card",
        back_populates="board_list",
        lazy="noload"
    )

    def populate_listcards(self, archived: bool = False):
        """Loads cards of the list.

        Args:
            archived (bool, optional): Should we load archived cards? Defaults to False.
        """
        self.cards = Card.query.filter(
            sqla.and_(
                Card.list_id == self.id,
                Card.archived == archived
            )
        ).order_by(Card.position.asc()).all()
