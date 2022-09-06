import json
import typing
from werkzeug.exceptions import Forbidden

from marshmallow.exceptions import ValidationError
import sqlalchemy as sqla

from api.app import db
from api.model import BoardPermission, CardActivityEvent
from api.model.board import BoardAllowedUser
from api.model.user import User
from api.model.list import BoardList
from api.model.card import (
    Card, CardActivity, CardComment, CardChecklist, ChecklistItem
)


def get_card(current_user: User, card_id: int) -> Card:
    """Gets card if user can access the board

    Args:
        current_user (User): Current user
        card_id (int): Card ID:

    Returns:
        Card: Card ORM object.
    """
    card = Card.get_or_404(card_id)
    if card.board.is_user_can_access(current_user.id):
        return card
    raise Forbidden()


def get_cards(current_user: User, board_list: BoardList) -> typing.List[Card]:
    """Gets cards from board list

    Args:
        current_user (User): Logged in user
        board_list (BoardList): Board list

    Returns:
        typing.List[Card]: List of cards
    """
    if (
        board_list.board.is_user_can_access(current_user.id)
    ):
        return board_list.cards
    raise Forbidden()


def post_card(current_user: User, board_list: BoardList, data: dict) -> Card:
    """Creates a card.

    Args:
        current_user (User): Logged in user
        board_list (BoardList): Board list

    Raises:
        Forbidden: Don't have permission to create card

    Returns:
        Card: Card ORM object
    """
    if (
        board_list.board.has_permission(
            current_user.id, BoardPermission.CARD_EDIT
        )
    ):
        card = Card(
            owner_id=current_user.id,
            board_id=board_list.board_id,
            **data
        )
        position_max = db.engine.execute(
            f"SELECT MAX(position) FROM card WHERE list_id={board_list.id}"
        ).fetchone()
        if position_max[0] is not None:
            card.position = position_max[0] + 1
        return card
    raise Forbidden()


def patch_card(current_user: User, card: Card, data: dict) -> Card:
    """Updates a card

    Args:
        current_user (User): Logged in user
        card (Card): Card ORM object to update
        data (dict): Update data

    Raises:
        Forbidden: Don't have permission to update card

    Returns:
        Card: Updated card ORM object
    """
    if (
        card.board.has_permission(
            current_user.id, BoardPermission.CARD_EDIT
        )
    ):
        for key, value in data.items():
            if key == "list_id" and card.list_id != value:
                # Get target list id
                target_list = BoardList.get_or_404(value)
                activity = CardActivity(
                    user_id=current_user.id,
                    event=CardActivityEvent.CARD_MOVE_TO_LIST.value,
                    entity_id=card.id,
                    changes=json.dumps(
                        {
                            "from": {
                                "id": card.list_id,
                                "title": card.board_list.title
                            },
                            "to": {
                                "id": value,
                                "title": target_list.title
                            }
                        }
                    )
                )
                card.activities.append(activity)
                card.list_id = value
            elif hasattr(card, key):
                setattr(card, key, value)
        return card
    raise Forbidden()


def post_card_comment(
    current_user: User, card: Card, data: dict
) -> CardActivity:
    if (
        card.board.has_permission(
            current_user.id, BoardPermission.CARD_COMMENT
        )
    ):
        comment = CardComment(
            user_id=current_user.id,
            board_id=card.board_id,
            **data
        )
        activity = CardActivity(
            user_id=current_user.id,
            event=CardActivityEvent.CARD_COMMENT.value,
            entity_id=comment.id,
            comment=comment
        )
        card.activities.append(activity)
        return activity
    raise Forbidden()


def patch_card_comment(
    current_user: User, comment: CardComment, data: dict
) -> CardComment:
    user_can_edit = (
        comment.user_id == current_user.id and
        comment.board.has_permission(
            current_user.id,
            BoardPermission.CARD_COMMENT
        )
    )
    if (user_can_edit):
        comment.update(**data)
        comment.card.activities.append(
            CardActivity(
                user_id=current_user.id,
                event=CardActivityEvent.CARD_COMMENT.value,
                entity_id=comment.id
            )
        )


def delete_card_comment(current_user: User, comment: CardComment):
    user_can_delete = (
        comment.user_id == current_user.id and
        comment.card.board_list.board.is_user_can_access(current_user.id)
    )

    if (user_can_delete):
        comment.delete()
    else:
        raise Forbidden()


def delete_card(current_user: User, card: Card):
    """Deletes a card.

    Args:
        current_user (User): Logged in user
        card (Card): Card ORM object  to delete

    Raises:
        Forbidden: Don't have permission to delete card
    """
    if (
        card.board_list.board.has_permission(
            current_user.id, BoardPermission.CARD_EDIT
        )
    ):
        db.session.delete(card)
    else:
        raise Forbidden()


def get_card_activities(current_user: User, card: Card):
    if card.board.is_user_can_access(current_user.id):
        return card.activities
    raise Forbidden()


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
