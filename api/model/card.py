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
    user_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("user.id"), nullable=False)
    activity_on = sqla.Column(
        sqla.DateTime(timezone=True),
        default=datetime.utcnow
    )

    entity_id = sqla.Column(sqla.Integer)
    event = sqla.Column(sqla.SmallInteger, nullable=False)

    # Card
    card = sqla_orm.relationship("Card", uselist=False)

    # User
    user = sqla_orm.relationship("User", uselist=False)

    # Relationships
    list_change = sqla_orm.relationship(
        "CardListChange", cascade="all, delete-orphan", uselist=False
    )
    comment = sqla_orm.relationship(
        "CardComment", cascade="all, delete-orphan", uselist=False,
    )
    member = sqla_orm.relationship(
        "CardMember", cascade="all, delete-orphan", uselist=False,
    )
    checklist = sqla_orm.relationship(
        "CardChecklist", cascade="all, delete-orphan", uselist=False,
    )
    checklist_item = sqla_orm.relationship(
        "ChecklistItem", cascade="all, delete-orphan", uselist=False,
    )


class CardListChange(db.Model, BaseMixin):
    """Card moved to to other list event"""
    __tablename__ = "card_list_assignment"

    id = sqla.Column(sqla.Integer, primary_key=True)
    activity_id = sqla.Column(sqla.Integer, sqla.ForeignKey("card_activity.id"))

    from_list_id = sqla.Column(sqla.Integer, sqla.ForeignKey("list.id"))
    to_list_id = sqla.Column(sqla.Integer, sqla.ForeignKey("list.id"))

    from_list = sqla_orm.relationship("BoardList", foreign_keys=[from_list_id])
    to_list = sqla_orm.relationship("BoardList", foreign_keys=[to_list_id])


class CardMember(db.Model, BaseMixin):
    """Card member assignment"""
    __tablename__ = "card_member_assignment"

    id = sqla.Column(sqla.Integer, primary_key=True)

    activity_id = sqla.Column(
        sqla.ForeignKey("card_activity.id"), nullable=False)
    user_id = sqla.Column(sqla.ForeignKey("user.id"), nullable=False)

    send_notification = sqla.Column(sqla.Boolean, default=True, nullable=False)

    user = sqla_orm.relationship("User")


class ChecklistItem(db.Model, BaseMixin):
    """Card checklist item"""
    __tablename__ = "card_checklist_item"
    id = sqla.Column(sqla.Integer, primary_key=True)
    activity_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("card_activity.id"))
    checklist_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("card_checklist.id"))
    title = sqla.Column(sqla.Text)
    completed = sqla.Column(sqla.Boolean, default=False, nullable=False)


class CardChecklist(db.Model, BaseMixin):
    """Card checklist"""

    __tablename__ = "card_checklist"
    id = sqla.Column(sqla.Integer, primary_key=True)
    activity_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("card_activity.id"))

    items = sqla_orm.relationship(
        "ChecklistItem", cascade="all, delete-orphan")


class CardComment(db.Model, BaseMixin):
    __tablename__ = "card_comment"
    id = sqla.Column(sqla.Integer, primary_key=True)
    user_id = sqla.Column(sqla.Integer, sqla.ForeignKey("user.id"))
    activity_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("card_activity.id"))

    comment = sqla.Column(sqla.Text)

    created = sqla.Column(
        sqla.DateTime(timezone=True), default=datetime.utcnow
    )
    updated = sqla.Column(sqla.DateTime(timezone=True))

    activity = sqla_orm.relationship("CardActivity", back_populates="comment")

    def update(self, **kwargs):
        self.update(**kwargs)
        self.updated = datetime.utcnow()


class Card(db.Model, BaseMixin):

    __tablename__ = "card"

    id = sqla.Column(sqla.Integer, primary_key=True)
    list_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("list.id"), nullable=False)
    owner_id = sqla.Column(
        sqla.Integer, sqla.ForeignKey("user.id"), nullable=False)

    title = sqla.Column(sqla.Text, nullable=False)
    description = sqla.Column(sqla.Text)
    due_date = sqla.Column(sqla.DateTime(timezone=True))
    position = sqla.Column(sqla.SmallInteger, default=0)

    board_list = sqla_orm.relationship(
        "BoardList", back_populates="cards"
    )
    activities = sqla_orm.relationship(
        "CardActivity", cascade="all, delete-orphan",
        back_populates="card",
        order_by="desc(CardActivity.activity_on)"
    )
