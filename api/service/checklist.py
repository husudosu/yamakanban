from datetime import datetime
import typing
import json

from werkzeug.exceptions import Forbidden
import sqlalchemy as sqla
from marshmallow.exceptions import ValidationError

from api.app import db
from api.model import BoardPermission, CardActivityEvent
from api.model.board import BoardAllowedUser
from api.model.card import CardActivity, Card
from api.model.checklist import CardChecklist, ChecklistItem


def post_card_checklist(
    current_member: BoardAllowedUser,
    card: Card,
    data: dict
) -> CardChecklist:
    if (current_member.has_permission(BoardPermission.CHECKLIST_CREATE)):
        # Create checklist
        checklist = CardChecklist(
            card_id=card.id,
            board_id=card.board_id,
            **data
        )

        # Card activity
        card.activities.append(
            CardActivity(
                board_user_id=current_member.id,
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
    current_member: BoardAllowedUser,
    checklist: CardChecklist,
    data: dict
) -> CardChecklist:
    if current_member.has_permission(BoardPermission.CHECKLIST_EDIT):
        checklist.update(**data)
        return checklist
    raise Forbidden()


def delete_card_checklist(
    current_member: BoardAllowedUser,
    checklist: CardChecklist
):
    if (current_member.has_permission(BoardPermission.CHECKLIST_EDIT)):
        db.session.delete(checklist)
        checklist.card.activities.append(
            CardActivity(
                board_user_id=current_member.id,
                event=CardActivityEvent.CHECKLIST_DELETE.value
            )
        )
    else:
        raise Forbidden()


def post_checklist_item(
    current_member: BoardAllowedUser,
    checklist: CardChecklist,
    data: dict
) -> ChecklistItem:
    if current_member.has_permission(BoardPermission.CHECKLIST_EDIT):
        errors = {}
        assigned_user = None

        # Validate some SQL sutff if required.
        if data.get("marked_complete_board_user_id"):
            if not checklist.board.get_board_user(data["marked_complete_board_user_id"]):
                errors["marked_complete_board_user_id"] = [
                    "User not exists or not member of board!"]

        if data.get("assigned_board_user_id"):
            assigned_user = checklist.board.get_board_user(
                data["assigned_board_user_id"])

            if not assigned_user:
                errors["assigned_board_user_id"] = [
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


def checklist_item_process_changes(
    current_member: BoardAllowedUser, item: ChecklistItem, data: dict
):
    """Processes data changes of checklist item, creates card activities
    based on data changes.

    Args:
        current_member (User): Current logged in board member
        item (ChecklistItem): Checklist item to process
        data (dict): Data got from request
    """
    if (
        data.get("completed") is not None and
        data["completed"] != item.completed
    ):
        # Checklist item marked
        activity = CardActivity(
            board_user_id=current_member.id,
            event=CardActivityEvent.CHECKLIST_ITEM_MARKED,
            entity_id=item.id,
            changes=json.dumps(
                {
                    "to": {
                        "title": item.title,
                        "completed": data["completed"]
                    }
                }
            )
        )
        item.checklist.card.activities.append(activity)
        # Update details
        if data["completed"]:
            item.marked_complete_board_user_id = current_member.id
            item.marked_complete_on = datetime.utcnow()
        else:
            item.marked_complete_user_id = None
            item.marked_complete_on = None
    # TODO: Add all checklist item events here!


def patch_checklist_item(
    current_member: BoardAllowedUser,
    item: ChecklistItem,
    data: dict
) -> ChecklistItem:
    errors = {}
    if current_member.has_permission(BoardPermission.CHECKLIST_EDIT):
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

        checklist_item_process_changes(current_member, item, data)

        item.update(**data)
        return item
    elif current_member.has_permission(BoardPermission.CHECKLIST_ITEM_MARK):
        # Only allow marking for member
        # TODO: raise forbidden if there's other fields on data
        checklist_item_process_changes(current_member, item, data)
        item.update(completed=data["completed"])
        return item
    raise Forbidden()


def delete_checklist_item(
    current_member: BoardAllowedUser,
    item: ChecklistItem
):
    if current_member.has_permission(BoardPermission.CHECKLIST_EDIT):
        db.session.delete(item)
    else:
        raise Forbidden()


def update_items_position(
    current_member: BoardAllowedUser, checklist: CardChecklist, data: typing.List[int]
):
    if current_member.has_permission(BoardPermission.CHECKLIST_EDIT):
        for index, item in enumerate(data):
            db.session.query(ChecklistItem).filter(
                sqla.and_(
                    ChecklistItem.id == item,
                    ChecklistItem.checklist_id == checklist.id
                )
            ).update({"position": index})
