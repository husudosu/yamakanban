import json
import typing
from werkzeug.exceptions import Forbidden
from api.app import db
from api.model import BoardPermission, CardActivityEvent
from api.model.board import BoardAllowedUser
from api.model.user import User
from api.model.list import BoardList
from api.model.card import (
    Card, CardActivity, CardComment, CardChecklist, ChecklistItem
)
from api.util.schemas import ChecklistItemSchema


def get_card(current_user: User, card_id: int) -> Card:
    """Gets card if user can access the board

    Args:
        current_user (User): Current user
        card_id (int): Card ID:

    Returns:
        Card: Card ORM object.
    """
    card = Card.get_or_404(card_id)
    can_access = (
        card.board_list.board.is_user_can_access(current_user.id) or
        current_user.has_role("admin")
    )
    if can_access:
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
        board_list.board.is_user_can_access(current_user.id) or
        current_user.has_role("admin")
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
        card = Card(owner_id=current_user.id, **data)
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
        card.board_list.board.has_permission(
            current_user.id, BoardPermission.CARD_EDIT
        ) or
        current_user.has_role("admin")
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
        card.board_list.board.has_permission(
            current_user.id, BoardPermission.CARD_COMMENT
        ) or
        current_user.has_role("admin")
    ):
        comment = CardComment(user_id=current_user.id, **data)
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
        comment.card.board_list.board.is_user_can_access(current_user.id)
    )
    if (
        user_can_edit or
        current_user.has_role("admin")
    ):
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

    if (
        user_can_delete or
        current_user.has_role("admin")
    ):
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
    if (
        card.board_list.board.is_user_can_access(current_user.id) or
        current_user.has_role("admin")
    ):
        return card.activities
    raise Forbidden()


def post_card_checklist(
    current_user: User,
    card: Card,
    data: dict
) -> CardChecklist:
    board_user: BoardAllowedUser = card.board_list.board.get_board_user(
        current_user.id)
    if (
        board_user and
        board_user.has_permission(BoardPermission.CHECKLIST_CREATE)
    ):
        # Create checklist
        checklist = CardChecklist(card_id=card.id, **data)

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
    # TODO: Maybe we should find better way to get board_user.
    board_user: BoardAllowedUser = \
        checklist.card.board_list.board.get_board_user(
            current_user.id
        )
    if (
        board_user and
        board_user.has_permission(BoardPermission.CHECKLIST_EDIT)
    ):
        checklist.update(**data)
        return checklist
    raise Forbidden()


def delete_card_checklist(
    current_user: User,
    checklist: CardChecklist
):
    # TODO: Maybe we should find better way to get board_user.
    board_user: BoardAllowedUser = \
        checklist.card.board_list.board.get_board_user(
            current_user.id
        )
    if (
        board_user and
        board_user.has_permission(BoardPermission.CHECKLIST_EDIT)
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


def add_checklist_item(
    current_user: User,
    checklist: CardChecklist,
    data: dict
) -> ChecklistItem:
    raise NotImplemented()


def patch_checklist_item(
    current_user: User,
    item: ChecklistItem,
    data: dict
) -> ChecklistItem:
    raise NotImplemented()


def delete_checklist_item(
    current_user: User,
    item: ChecklistItem
):
    pass
