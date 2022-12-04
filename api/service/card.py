import json
from werkzeug.exceptions import Forbidden, NotFound
from datetime import datetime
from marshmallow.exceptions import ValidationError
import sqlalchemy as sqla
from flask_sqlalchemy import Pagination

from api.app import db, socketio

from api.model.user import User
from api.model.card import Card, CardActivity, CardComment, CardMember, CardDate
from api.model import BoardPermission, CardActivityEvent
from api.model.board import BoardAllowedUser
from api.model.list import BoardList

from api.util.dto import SIODTO, CardDTO
from api.socket import SIOEvent


class CardService:
    """
    Contains business logic for Card.
    """

    def get(self, current_user: User, id: int, args: dict) -> Card:
        """Gets card if the user has permission.

        Args:
            current_user (User): Current logged in user
            id (int): Card ID to get.
            args (dict): Args got from query.

        Raises:
            Forbidden: User not member of board.

        Returns:
            Card: Card ORM object
        """
        # Check permission
        card: Card = Card.get_or_404(id)

        # Only membership required for getting card info.
        BoardAllowedUser.get_by_usr_or_403(card.board_id, current_user.id)

        # Load card activities
        card.activities = CardActivity.query.filter(
            CardActivity.card_id == card.id
        ).order_by(
            sqla.desc(CardActivity.activity_on)
        ).limit(args["activity_count"]).all()

        return card

    def get_activities(self, current_user: User, card_id: int, args: dict) -> Pagination:
        """Gets card activities

        Args:
            current_user (User): Current logged in user
            card_id (int): Card ID to get.
            args (dict): Query parameters got from ma schema.

        Returns:
            Pagination: Flask sqlalchemy pagination object.
        """
        print(args)
        card: Card = Card.get_or_404(card_id)
        # Only membership required for getting card activities.
        BoardAllowedUser.get_by_usr_or_403(card.board_id, current_user.id)

        # Query and paginate
        query = CardActivity.query.filter(CardActivity.card_id == card_id)

        # Checks type
        if args["type"] == "comment":
            query = query.filter(
                CardActivity.event == CardActivityEvent.CARD_COMMENT.value)

        # Get between two dates
        if "dt_from" in args.keys() and "dt_to" in args.keys():
            query = query.filter(
                CardActivity.activity_on.between(
                    args["dt_from"],
                    args["dt_to"]
                )
            )
        elif "dt_from" in args.keys():
            query = query.filter(
                CardActivity.activity_on >= args["dt_from"]
            )
        elif "dt_to" in args.keys():
            query = query.filter(
                CardActivity.activity_on < args["dt_to"]
            )

        # Filter by user id
        if "board_user_id" in args.keys():
            query = query.filter(
                CardActivity.board_user_id == args["board_user_id"]
            )

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

    def post(self, current_user: User, list_id: int, data: dict) -> Card:
        """Creates a card.

        Args:
            current_user (User): Current logged in user
            list_id (int): Board list ID where we need the card.
            data (dict): Card data as dict

        Raises:
            Forbidden: Don't have permission to create  cards

        Returns:
            Card: Card ORM object.
        """
        board_list: BoardList = BoardList.get_or_404(list_id)
        current_member: BoardAllowedUser = BoardAllowedUser.get_by_usr_or_403(
            board_list.board_id, current_user.id)

        if current_member.has_permission(BoardPermission.CARD_EDIT):
            data.pop("list_id", None)
            data.pop("board_id", None)

            card = Card(
                **data,
                board_id=board_list.board_id,
                list_id=board_list.id
            )
            position_max = db.engine.execute(
                f"SELECT MAX(position) FROM card WHERE list_id={board_list.id}"
            ).fetchone()

            if position_max[0] is not None:
                card.position = position_max[0] + 1
            db.session.add(card)
            db.session.commit()

            socketio.emit(
                SIOEvent.CARD_NEW.value,
                CardDTO.card_schema.dump(card),
                namespace="/board",
                to=f"board-{card.board_id}"
            )

            return card

        raise Forbidden()

    def patch(self, current_user: User, card_id: int, data: dict) -> Card:
        """Updates card.

        Args:
            current_user (User): Current logged in user
            card_id (int): Card ID to update
            data (dict): Card update data

        Raises:
            ValidationError: _description_
            Forbidden: _description_

        Returns:
            Card: Returns updated card.
        """
        activities = []
        card: Card = Card.get_or_404(card_id)
        old_list_id = card.list_id

        current_member: BoardAllowedUser = BoardAllowedUser.get_by_usr_or_403(
            card.board_id, current_user.id
        )

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
                    activities.append(activity)
                elif hasattr(card, key):
                    setattr(card, key, value)

            db.session.commit()

            # Send card activities
            for activity in activities:
                socketio.emit(
                    SIOEvent.CARD_ACTIVITY.value,
                    CardDTO.activity_schema.dump(activity),
                    namespace="/board",
                    to=f"card-{card.id}"
                )

            dmp = CardDTO.update_card_schema.dump(card)
            socketio.emit(
                SIOEvent.CARD_UPDATE.value,
                SIODTO.event_schema.dump({
                    "list_id": old_list_id,
                    "card_id": card.id,
                    "entity": dmp
                }),
                namespace="/board",
                to=f"board-{card.board_id}"
            )
            return card
        raise Forbidden()

    def delete(self, current_user: User, card_id: int):
        """Deletes a card

        Args:
            current_user (User): Current logged in user.
            card_id (int): Card ID to delete.

        Raises:
            Forbidden: Don't have permission to delete cards
        """
        card: Card = Card.get_or_404(card_id)
        current_member = BoardAllowedUser.get_by_usr_or_403(
            card.board_id, current_user.id)

        if current_member.has_permission(BoardPermission.CARD_DELETE):
            list_id = card.list_id

            if not card.archived:
                card.archived = True
                card.archived_on = datetime.utcnow()
            else:
                db.session.delete(card)
            db.session.commit()

            socketio.emit(
                SIOEvent.CARD_DELETE.value,
                SIODTO.delete_event_scehma.dump(
                    {
                        "list_id": list_id,
                        "card_id": card_id,
                        "entity_id": card_id,
                    }
                ),
                namespace="/board",
                to=f"board-{card.board_id}"
            )

        else:
            raise Forbidden()


class CommentService:
    """
    Contains business logic for Card comment.
    """

    def post(self, current_user: User, card_id: int, data: dict) -> CardActivity:
        """Creates a card comment

        Args:
            current_user (User): Current logged in user
            card_id (int): Card id to add comment.
            data (dict): Comment data as dict

        Raises:
            Forbidden: Don't have permission to create comment.

        Returns:
            CardActivity: Card activity of comment
        """
        card: Card = Card.get_or_404(card_id)
        current_member: BoardAllowedUser = BoardAllowedUser.get_by_usr_or_403(
            card.board_id, current_user.id)

        if current_member.has_permission(BoardPermission.CARD_COMMENT):
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
            db.session.commit()

            socketio.emit(
                SIOEvent.CARD_ACTIVITY.value,
                CardDTO.activity_schema.dump(activity),
                namespace="/board",
                to=f"card-{card.id}"
            )

            return activity
        raise Forbidden()

    def patch(self, current_user: User, comment_id: int, data: dict) -> CardComment:
        comment: CardComment = CardComment.get_or_404(comment_id)
        current_member: BoardAllowedUser = BoardAllowedUser.get_by_usr_or_403(
            comment.board_id, current_user.id
        )

        if comment.board_user_id == current_member.id or current_member.role.is_admin:
            comment.update(**data)
            db.session.commit()

            socketio.emit(
                SIOEvent.CARD_ACTIVITY_UPDATE.value,
                CardDTO.activity_schema.dump(comment.activity),
                namespace="/board",
                to=f"card-{comment.activity.card_id}"
            )
            return comment
        raise Forbidden()

    def delete(self, current_user: User, comment_id: int):
        comment: CardComment = CardComment.get_or_404(comment_id)
        current_member: BoardAllowedUser = BoardAllowedUser.get_by_usr_or_403(
            comment.board_id, current_user.id
        )

        if comment.board_user_id == current_member.id or current_member.role.is_admin:
            activity_id, card_id = comment.activity_id, comment.activity.card_id
            db.session.delete(comment.activity)
            db.session.commit()

            socketio.emit(
                SIOEvent.CARD_ACTIVITY_DELETE.value,
                activity_id,
                namespace="/board",
                to=f"card-{card_id}"
            )
        else:
            raise Forbidden()


class MemberService:
    """
    Contains business logic for Member.
    """

    def post(self, current_user: User, card_id: int, data: dict) -> CardMember:
        """Assigns member to card.

        Args:
            current_user (User): Current logged in user
            card_id (int): Card to assign member
            data (dict): Member data as dict.

        Raises:
            ValidationError: Marshmallow validation error
            Forbidden: Don't have permission to assign mebmer.

        Returns:
            typing.Tuple[CardMember, CardActivity]: _description_
        """
        card: Card = Card.get_or_404(card_id)
        current_member: BoardAllowedUser = BoardAllowedUser.get_by_usr_or_403(
            card.board_id, current_user.id)
        if current_member.has_permission(BoardPermission.CARD_ASSIGN_MEMBER):
            member = BoardAllowedUser.query.filter(
                sqla.and_(
                    BoardAllowedUser.board_id == card.board_id,
                    BoardAllowedUser.id == data["board_user_id"]
                )
            ).first()
            if not member:
                raise ValidationError(
                    {"board_user_id": ["Board user not exists."]}
                )

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

            # Add card activity
            activity = CardActivity(
                card_id=card.id,
                board_user_id=current_member.id,
                event=CardActivityEvent.CARD_ASSIGN_MEMBER,
                entity_id=member.id,
                changes=json.dumps(
                    {"to": {"board_user_id": member_assignment.board_user_id}}
                )
            )
            card.activities.append(activity)
            db.session.commit()

            # Send card activity
            socketio.emit(
                SIOEvent.CARD_ACTIVITY.value,
                CardDTO.activity_schema.dump(activity),
                namespace="/board",
                to=f"card-{card.id}"
            )
            # Send member assigned
            socketio.emit(
                SIOEvent.CARD_MEMBER_ASSIGNED.value,
                SIODTO.event_schema.dump({
                    "list_id": card.list_id,
                    "card_id": card.id,
                    "entity": CardDTO.member_schema.dump(member_assignment)
                }),
                namespace="/board",
                to=f"board-{card.board_id}"
            )
            # TODO: Implement send notification

            return member_assignment
        raise Forbidden()

    def delete(self, current_user: User, card_id: int, card_member_id: int) -> CardActivity:
        """Deassigns card member.

        Args:
            current_user (User): Current logged in user.
            card_id (int): Card ID.
            card_member_id (int): Card Member ID

        Raises:
            Forbidden: Don't have permission to deassign member

        Returns:
            CardActivity: Card activity of deassignment.
        """
        card: Card = Card.get_or_404(card_id)
        current_member = BoardAllowedUser.get_by_usr_or_403(
            card.board_id, current_user.id)

        if current_member.has_permission(BoardPermission.CARD_DEASSIGN_MEMBER):
            # Get member
            card_member = CardMember.query.filter(
                sqla.and_(
                    CardMember.card_id == card.id,
                    CardMember.board_user_id == card_member_id
                )
            ).first()
            if not card_member:
                raise NotFound("Card member not exists.")

            entity_id = card_member.id

            # Add activity to card
            activity = CardActivity(
                card_id=card.id,
                board_user_id=current_member.id,
                event=CardActivityEvent.CARD_DEASSIGN_MEMBER,
                changes=json.dumps(
                    {"from": {"board_user_id": card_member.board_user_id}}
                )
            )
            card.activities.append(activity)
            db.session.delete(card_member)
            db.session.commit()

            socketio.emit(
                SIOEvent.CARD_ACTIVITY.value,
                CardDTO.activity_schema.dump(activity),
                namespace="/board",
                to=f"card-{card.id}"
            )
            # Send member assigned
            socketio.emit(
                SIOEvent.CARD_MEMBER_DEASSIGNED.value,
                SIODTO.delete_event_scehma.dump({
                    "list_id": card.list_id,
                    "card_id": card.id,
                    "entity_id": entity_id,
                }),
                namespace="/board",
                to=f"board-{card.board_id}"
            )
            return activity
        raise Forbidden()


class DateService:
    """
    Contains business logic for card date.
    """

    def post(self, current_user: User, card_id: int, data: dict) -> CardDate:
        """Creates Date."""
        card: Card = Card.get_or_404(card_id)
        current_member: BoardAllowedUser = BoardAllowedUser.get_by_usr_or_403(
            card.board_id, current_user.id)

        if current_member.has_permission(BoardPermission.CARD_ADD_DATE):
            card_date = CardDate(board_id=card.board_id, **data)
            card.dates.append(card_date)
            activity = CardActivity(
                board_user_id=current_member.id,
                event=CardActivityEvent.CARD_ADD_DATE,
                entity_id=card_date.id,
                changes=json.dumps(
                    {
                        "dt_from": card_date.dt_from.strftime("%Y-%m-%d %H:%M:%S") if card_date.dt_from else None,
                        "dt_to": card_date.dt_to.strftime("%Y-%m-%d %H:%M:%S"),
                        "description": card_date.description
                    }
                )
            )
            card.activities.append(activity)
            db.session.commit()

            socketio.emit(
                SIOEvent.CARD_ACTIVITY.value,
                CardDTO.activity_schema.dump(activity),
                namespace="/board",
                to=f"card-{card.id}"
            )

            socketio.emit(
                SIOEvent.CARD_DATE_NEW.value,
                SIODTO.event_schema.dump({
                    "card_id": card.id,
                    "list_id": card.list_id,
                    "entity": CardDTO.date_schema.dump(card_date)
                }),
                namespace="/board",
                to=f"board-{card.board_id}"
            )
            return card_date
        raise Forbidden()

    def patch(self, current_user: User, date_id: int, data: dict) -> CardDate:
        """Updates date.

        Args:
            current_user (User): Current logged in user.
            date_id (int): Card date id
            data (dict): Update data as dict

        Raises:
            Forbidden: No permission to update Card Date

        Returns:
            typing.Tuple[CardDate, CardActivity]: _description_
        """
        card_date = CardDate.get_or_404(date_id)
        current_member: BoardAllowedUser = BoardAllowedUser.get_by_usr_or_403(
            card_date.board_id, current_user.id)

        if current_member.has_permission(BoardPermission.CARD_EDIT_DATE):
            card_date.update(**data)
            activity = CardActivity(
                board_user_id=current_member.id,
                event=CardActivityEvent.CARD_EDIT_DATE,
                entity_id=card_date.id,
                changes=json.dumps(
                    {
                        "dt_from":  card_date.dt_from.strftime("%Y-%m-%d %H:%M:%S") if card_date.dt_from else None,
                        "dt_to": card_date.dt_to.strftime("%Y-%m-%d %H:%M:%S"),
                        "description": card_date.description
                    }
                )
            )
            card_date.card.activities.append(activity)
            db.session.commit()

            socketio.emit(
                SIOEvent.CARD_DATE_UPDATE.value,
                SIODTO.event_schema.dump(
                    {
                        "card_id": card_date.card_id,
                        "list_id": card_date.card.list_id,
                        "entity": CardDTO.date_schema.dump(card_date)
                    }
                ),
                namespace="/board",
                to=f"board-{card_date.board_id}"
            )

            return card_date
        raise Forbidden()

    def delete(self, current_user: User, date_id: int) -> CardActivity:
        """Delete card date.

        Args:
            current_user (User): Current logged in user.
            date_id (int): Date id to delete

        Raises:
            Forbidden: No permission to delete card date

        Returns:
            CardActivity: _description_
        """
        card_date = CardDate.get_or_404(date_id)
        current_member: BoardAllowedUser = BoardAllowedUser.get_by_usr_or_403(
            card_date.board_id, current_user.id)

        if current_member.has_permission(BoardPermission.CARD_EDIT_DATE):
            activity = CardActivity(
                board_user_id=current_member.id,
                event=CardActivityEvent.CARD_DELETE_DATE,
                entity_id=card_date.id,
            )
            # Dump event before deletion
            sio_event = SIODTO.delete_event_scehma.dump(
                {
                    "card_id": card_date.card_id,
                    "list_id": card_date.card.list_id,
                    "entity_id": card_date.id
                }
            )

            card_date.card.activities.append(activity)
            db.session.delete(card_date)
            db.session.commit()

            socketio.emit(
                SIOEvent.CARD_DATE_DELETE.value,
                sio_event,
                namespace="/board",
                to=f"board-{card_date.board_id}"
            )
        else:
            raise Forbidden()


card_service = CardService()
comment_service = CommentService()
member_service = MemberService()
date_service = DateService()
