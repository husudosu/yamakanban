import sqlalchemy as sqla
import sqlalchemy.orm as sqla_orm

from . import BaseMixin
from api.app import db


class ChecklistItem(db.Model, BaseMixin):
    """Card checklist item"""
    __tablename__ = "card_checklist_item"
    id = sqla.Column(sqla.Integer, primary_key=True)
    checklist_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("card_checklist.id"))
    marked_complete_user_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("user.id"))
    assigned_user_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("user.id")
    )
    board_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("board.id"), nullable=False
    )

    title = sqla.Column(sqla.Text)
    due_date = sqla.Column(sqla.DateTime)
    completed = sqla.Column(sqla.Boolean, default=False, nullable=False)
    marked_complete_on = sqla.Column(sqla.DateTime)

    board = sqla_orm.relationship("Board")


class CardChecklist(db.Model, BaseMixin):
    """Card checklist"""

    __tablename__ = "card_checklist"
    id = sqla.Column(sqla.Integer, primary_key=True)
    card_id = sqla.Column(sqla.Integer, sqla.ForeignKey("card.id"))
    board_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("board.id"), nullable=False
    )
    title = sqla.Column(sqla.Text)

    items = sqla_orm.relationship(
        "ChecklistItem", cascade="all, delete-orphan")
    card = sqla_orm.relationship(
        "Card", back_populates="checklists"
    )
    board = sqla_orm.relationship("Board")
