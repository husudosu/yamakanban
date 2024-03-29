import sqlalchemy as sqla
import sqlalchemy.orm as sqla_orm

from . import BaseMixin
from api.app import db


class ChecklistItem(db.Model, BaseMixin):
    """Card checklist item"""
    __tablename__ = "card_checklist_item"
    id = sqla.Column(sqla.Integer, primary_key=True)
    checklist_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("card_checklist.id", ondelete="CASCADE"))
    marked_complete_board_user_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("board_allowed_user.id", ondelete="CASCADE"))
    board_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("board.id", ondelete="CASCADE"), nullable=False
    )

    title = sqla.Column(sqla.Text)
    completed = sqla.Column(sqla.Boolean, default=False, nullable=False)
    marked_complete_on = sqla.Column(sqla.DateTime)
    position = sqla.Column(sqla.SmallInteger, default=0)
    board = sqla_orm.relationship("Board")

    checklist = sqla_orm.relationship("CardChecklist", back_populates="items")
    marked_complete_user = sqla_orm.relationship(
        "BoardAllowedUser", foreign_keys=[marked_complete_board_user_id], uselist=False)


class CardChecklist(db.Model, BaseMixin):
    """Card checklist"""

    __tablename__ = "card_checklist"
    id = sqla.Column(sqla.Integer, primary_key=True)
    card_id = sqla.Column(sqla.Integer, sqla.ForeignKey(
        "card.id", ondelete="CASCADE"))
    board_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("board.id", ondelete="CASCADE"), nullable=False
    )
    title = sqla.Column(sqla.Text)

    items = sqla_orm.relationship(
        "ChecklistItem",
        cascade="all, delete-orphan",
        order_by="asc(ChecklistItem.position)"
    )
    card = sqla_orm.relationship(
        "Card", back_populates="checklists"
    )
    board = sqla_orm.relationship("Board")
