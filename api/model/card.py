from datetime import datetime
import sqlalchemy as sqla
import sqlalchemy.orm as sqla_orm

from api.app import db
from . import BaseMixin


class CardActivity(db.Model, BaseMixin):
    """Card activity log"""
    __tablename__ = "card_activity"
    id = sqla.Column(sqla.Integer, primary_key=True)
    card_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("card.id"), nullable=False)
    board_user_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("board_allowed_user.id"), nullable=False)
    activity_on = sqla.Column(
        sqla.DateTime,
        default=datetime.utcnow
    )

    entity_id = sqla.Column(sqla.Integer)
    event = sqla.Column(sqla.SmallInteger, nullable=False)  # CardActivityEvent
    changes = sqla.Column(sqla.Text, default="{}")

    # Card
    card = sqla_orm.relationship("Card", uselist=False)

    # User
    board_user = sqla_orm.relationship("BoardAllowedUser", uselist=False)

    comment = sqla_orm.relationship(
        "CardComment", cascade="all, delete-orphan", uselist=False,
    )


class CardMember(db.Model, BaseMixin):
    """Card member assignment"""
    __tablename__ = "card_member_assignment"

    id = sqla.Column(sqla.Integer, primary_key=True)

    card_id = sqla.Column(
        sqla.ForeignKey("card.id"), nullable=False)
    board_user_id = sqla.Column(sqla.ForeignKey(
        "board_allowed_user.id"), nullable=False)

    send_notification = sqla.Column(sqla.Boolean, default=True, nullable=False)

    board_user = sqla_orm.relationship("BoardAllowedUser")


class CardComment(db.Model, BaseMixin):
    __tablename__ = "card_comment"
    id = sqla.Column(sqla.Integer, primary_key=True)
    board_user_id = sqla.Column(sqla.ForeignKey(
        "board_allowed_user.id"), nullable=False)
    activity_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("card_activity.id"))
    board_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("board.id"), nullable=False
    )

    comment = sqla.Column(sqla.Text)

    created = sqla.Column(
        sqla.DateTime, default=datetime.utcnow
    )
    updated = sqla.Column(sqla.DateTime)

    activity = sqla_orm.relationship("CardActivity", back_populates="comment")
    board = sqla_orm.relationship("Board")

    def update(self, **kwargs):
        self.update(**kwargs)
        self.updated = datetime.utcnow()


class Card(db.Model, BaseMixin):

    __tablename__ = "card"

    id = sqla.Column(sqla.Integer, primary_key=True)
    list_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("list.id"), nullable=False)
    owner_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("board_allowed_user.id"), nullable=False)
    board_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("board.id"), nullable=False
    )

    title = sqla.Column(sqla.Text, nullable=False)
    description = sqla.Column(sqla.Text)
    due_date = sqla.Column(sqla.DateTime)
    position = sqla.Column(sqla.SmallInteger, default=0)

    board_list = sqla_orm.relationship(
        "BoardList", back_populates="cards"
    )
    activities = sqla_orm.relationship(
        "CardActivity", cascade="all, delete-orphan",
        back_populates="card",
        order_by="desc(CardActivity.activity_on)"
    )
    checklists = sqla_orm.relationship(
        "CardChecklist", cascade="all, delete-orphan",
    )
    assigned_members = sqla_orm.relationship(
        "CardMember", cascade="all, delete-orphan"
    )

    board = sqla_orm.relationship("Board")
