import json
import typing
from werkzeug.exceptions import Forbidden
from marshmallow.exceptions import ValidationError
import sqlalchemy as sqla

from api.app import db
from api.model import BoardPermission, CardActivityEvent
from api.model.board import BoardAllowedUser

from api.model.list import BoardList
from api.model.card import (
    Card, CardActivity, CardComment, CardMember
)


def get_card(card_id: int) -> Card:
    """Gets card if user can access the board
    Args:
        card_id (int): Card ID:
    Returns:
        Card: Card ORM object.
    """
    card = Card.get_or_404(card_id)
    return card


def get_cards(board_list: BoardList) -> typing.List[Card]:
    """Gets cards from board list

    Args:
        board_list (BoardList): Board list

    Returns:
        typing.List[Card]: List of cards
    """
    return board_list.cards


def post_card(current_member: BoardAllowedUser, board_list: BoardList, data: dict) -> Card:
    """Creates a card.

    Args:
        current_member (User): Current logged in board member
        board_list (BoardList): Board list

    Raises:
        Forbidden: Don't have permission to create card

    Returns:
        Card: Card ORM object
    """
    if current_member.has_permission(BoardPermission.CARD_EDIT):
        data.pop("list_id", None)
        card = Card(
            **data,
            owner_id=current_member.id,
            board_id=board_list.board_id,
            list_id=board_list.id,
        )
        position_max = db.engine.execute(
            f"SELECT MAX(position) FROM card WHERE list_id={board_list.id}"
        ).fetchone()
        if position_max[0] is not None:
            card.position = position_max[0] + 1
        return card
    raise Forbidden()


def patch_card(current_member: BoardAllowedUser, card: Card, data: dict) -> Card:
    """Updates a card

    Args:
        current_member (BoardAllowedUser): Current logged in board member
        card (Card): Card ORM object to update
        data (dict): Update data

    Raises:
        Forbidden: Don't have permission to update card

    Returns:
        Card: Updated card ORM object
    """
    if (current_member.has_permission(BoardPermission.CARD_EDIT)):
        for key, value in data.items():
            if key == "list_id" and card.list_id != value:
                # Get target list id
                target_list: BoardList = BoardList.get_or_404(value)

                if target_list.board_id != card.board_id:
                    raise ValidationError(
                        {"list_id": ["Cannot move card to other board!"]})

                activity = CardActivity(
                    board_user_id=current_member.id,
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
    current_member: BoardAllowedUser, card: Card, data: dict
) -> CardActivity:
    if (
        current_member.has_permission(BoardPermission.CARD_COMMENT)
    ):
        comment = CardComment(
            board_user_id=current_member.id,
            board_id=card.board_id,
            **data
        )
        activity = CardActivity(
            board_user_id=current_member.id,
            event=CardActivityEvent.CARD_COMMENT.value,
            entity_id=comment.id,
            comment=comment
        )
        card.activities.append(activity)
        return activity
    raise Forbidden()


def patch_card_comment(
    current_member: BoardAllowedUser, comment: CardComment, data: dict
) -> CardComment:
    if (comment.board_user_id == current_member.id):
        comment.update(**data)
        comment.card.activities.append(
            CardActivity(
                board_user_id=current_member.id,
                event=CardActivityEvent.CARD_COMMENT.value,
                entity_id=comment.id
            )
        )
        return comment
    raise Forbidden()


def delete_card_comment(
    current_member: BoardAllowedUser, comment: CardComment
):
    if (current_member.id == comment.board_user_id):
        comment.delete()
    else:
        raise Forbidden()


def delete_card(current_member: BoardAllowedUser, card: Card):
    """Deletes a card.
    Args:
        current_member (BoardAllowedUser): Current logged in board member
        card (Card): Card ORM object  to delete

    Raises:
        Forbidden: Don't have permission to delete card
    """
    if current_member.has_permission(BoardPermission.CARD_DELETE):
        db.session.delete(card)
    else:
        raise Forbidden()


def get_card_activities(card: Card, args: dict = {}):
    # Query and paginate
    query = CardActivity.query.filter(CardActivity.card_id == card.id)
    # Checks type
    if args["type"] == "comment":
        query = query.filter(CardActivity.event ==
                             CardActivityEvent.CARD_COMMENT.value)

    # Sortby
    sortby = args.get("sort_by", "activity_on")
    order = args.get("order", "desc")

    if not hasattr(CardActivity, sortby):
        sortby = "activity_on"

    if order == "asc":
        query = query.order_by(sqla.asc(getattr(CardActivity, sortby)))
    elif order == "desc":
        query = query.order_by(sqla.desc(getattr(CardActivity, sortby)))

    return query.paginate(args["page"], args["per_page"])


def assign_card_member(
    current_member: BoardAllowedUser, card: Card,
    data: dict
) -> CardMember:
    if current_member.has_permission(BoardPermission.CARD_ASSIGN_MEMBER):
        # Get member
        member = BoardAllowedUser.query.filter(
            BoardAllowedUser.id == data["board_user_id"]
        ).first()

        if not member:
            raise ValidationError(
                {"board_user_id": ["Board user not exists."]})

        # Check if member already assigned
        if CardMember.query.filter(
            sqla.and_(
                CardMember.card_id == card.id,
                CardMember.board_user_id == member.id
            )
        ).first():
            raise ValidationError(
                {"board_user_id": ["Member already assigned to this card."]})

        member_assignment = CardMember(board_user_id=member.id)
        card.assigned_members.append(member_assignment)
        # TODO: Implement send notification

        # Add card activity
        card.activities.append(
            CardActivity(
                board_user_id=current_member.id,
                event=CardActivityEvent.CARD_ASSIGN_MEMBER,
                entity_id=member.id,
                changes=json.dumps(
                    {"to": {"board_user_id": member_assignment.board_user_id}}
                )
            )
        )
        return member_assignment
    raise Forbidden()


def deassign_card_member(
    current_member: BoardAllowedUser, card: Card,
    data: dict
):
    if current_member.has_permission(BoardPermission.CARD_DEASSIGN_MEMBER):
        # Get member
        card_member: CardMember = CardMember.query.filter(
            sqla.and_(
                CardMember.card_id == card.id,
                CardMember.board_user_id == data["board_user_id"]
            )
        ).first()

        if not card_member:
            raise ValidationError(
                {"board_user_id": ["Board user not assigned to this card."]}
            )
        # Add activity to card
        card.activities.append(
            CardActivity(
                board_user_id=current_member.id,
                event=CardActivityEvent.CARD_DEASSIGN_MEMBER,
                changes=json.dumps(
                    {"from": {"board_user_id": card_member.board_user_id}}
                )
            )
        )
        db.session.delete(card_member)
    else:
        raise Forbidden()
