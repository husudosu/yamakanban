import typing
import json

from werkzeug.exceptions import Forbidden
import sqlalchemy as sqla
from marshmallow.exceptions import ValidationError

from api.app import db
from api.model import BoardPermission, CardActivityEvent
from api.model.user import User
from api.model.board import BoardAllowedUser
from api.model.card import CardActivity, Card
from api.model.checklist import CardChecklist, ChecklistItem


def post_card_checklist(
    current_user: User,
    card: Card,
    data: dict
) -> CardChecklist:
    if (
        card.board.has_permission(
            current_user.id, BoardPermission.CHECKLIST_CREATE)
    ):
        # Create checklist
        checklist = CardChecklist(
            card_id=card.id,
            board_id=card.board_id,
            **data
        )

        # Card activity
        card.activities.append(
            CardActivity(
                user_id=current_user.id,
                event=CardActivityEvent.CHECKLIST_CREATE.value,
                entity_id=card.id,
                changes=json.dumps({
                    "to": {
                        "title": checklist.title
                    }
                })
            )
        )
        return checklist
    raise Forbidden()


def patch_card_checklist(
    current_user: User,
    checklist: CardChecklist,
    data: dict
) -> CardChecklist:
    if (
        checklist.board.has_permission(
            current_user.id, BoardPermission.CHECKLIST_EDIT)
    ):
        checklist.update(**data)
        return checklist
    raise Forbidden()


def delete_card_checklist(
    current_user: User,
    checklist: CardChecklist
):
    if (
        checklist.board.has_permission(
            current_user.id, BoardPermission.CHECKLIST_EDIT)
    ):
        db.session.delete(checklist)
        checklist.card.activities.append(
            CardActivity(
                user_id=current_user.id,
                event=CardActivityEvent.CHECKLIST_DELETE.value
            )
        )
    else:
        raise Forbidden()


def validate_user(board_id: int, fieldname: str, user_id: int) -> typing.Dict:
    # TODO: Need better SQL side validation than this
    usr = User.query.get(user_id)
    errors = {}
    if not usr:
        errors[fieldname] = ["User not exists."]
    else:
        if not BoardAllowedUser.query.filter(
            sqla._and(
                BoardAllowedUser.user_id == usr.id,
                BoardAllowedUser.board_id == board_id
            )
        ).first():
            errors[fieldname] = [
                "User not member of board."]
    return errors


def post_checklist_item(
    current_user: User,
    checklist: CardChecklist,
    data: dict
) -> ChecklistItem:
    if (
        checklist.board.has_permission(
            current_user.id, BoardPermission.CHECKLIST_EDIT)
    ):
        errors = {}
        assigned_user = None

        # Validate some SQL sutff if required.
        if data.get("marked_complete_user_id"):
            if not checklist.board.get_board_user(data["marked_complete_user_id"]):
                errors["marked_complete_user_id"] = [
                    "User not exists or not member of board!"]

        if data.get("assigned_user_id"):
            assigned_user = checklist.board.get_board_user(
                data["assigned_user_id"])

            if not assigned_user:
                errors["assigned_user_id"] = [
                    "User not exists or not member of board!"]

        if len(errors.keys()) > 0:
            raise ValidationError(errors)

        item = ChecklistItem(
            board_id=checklist.board_id,
            **data
        )

        # Calculate position
        position_max = db.engine.execute(
            f"SELECT MAX(position) FROM card_checklist_item WHERE checklist_id={checklist.id}"
        ).fetchone()
        if position_max[0] is not None:
            item.position = position_max[0] + 1

        checklist.items.append(item)
        # TODO Send Email notification for assigned user
        return item
    raise Forbidden()


def patch_checklist_item(
    current_user: User,
    item: ChecklistItem,
    data: dict
) -> ChecklistItem:
    errors = {}
    if item.board.has_permission(
            current_user.id, BoardPermission.CHECKLIST_EDIT):
        # User can update everything

        # SQL validation
        if data.get("marked_complete_user_id"):
            if not item.board.get_board_user(data["marked_complete_user_id"]):
                errors["marked_complete_user_id"] = [
                    "User not exists or not member of board!"]

        if data.get("assigned_user_id"):
            assigned_user = item.board.get_board_user(
                data["assigned_user_id"])

            if not assigned_user:
                errors["assigned_user_id"] = [
                    "User not exists or not member of board!"]

        if len(errors.keys()) > 0:
            raise ValidationError(errors)
        item.update(**data)
        return item
    elif item.board_has_permission(
            current_user.id, BoardPermission.CHECKLIST_ITEM_MARK):
        # Only allow marking for member
        # TODO: raise forbidden if there's other fields on data
        item.update(marked_complete_on=data["marked_complete_on"])
        return item
    raise Forbidden()


def delete_checklist_item(
    current_user: User,
    item: ChecklistItem
):
    if item.board.has_permission(
            current_user.id, BoardPermission.CHECKLIST_EDIT):
        db.session.delete(item)
    else:
        raise Forbidden()


def update_items_position(
    current_user: User, checklist: CardChecklist, data: typing.List[int]
):
    if checklist.board.is_user_can_access(current_user.id):
        for index, item in enumerate(data):
            db.session.query(ChecklistItem).filter(
                sqla.and_(
                    ChecklistItem.id == item,
                    ChecklistItem.checklist_id == checklist.id
                )
            ).update({"position": index})
