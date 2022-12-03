from api.util import schemas


class CardDTO:
    card_schema = schemas.CardSchema()
    update_card_schema = schemas.CardSchema(exclude=("activities",))

    comment_schema = schemas.CardCommentSchema()

    activity_schema = schemas.CardActivitySchema()
    activity_paginated_schema = schemas.CardActivityPaginatedSchema()
    activity_schema_query = schemas.CardActivityQuerySchema()

    member_schema = schemas.CardMemberSchema()
    date_schema = schemas.CardDateSchema()
    query_schema = schemas.CardQuerySchema()


class ChecklistDTO:
    checklist_schema = schemas.CardChecklistSchema()
    checklist_new_schema = schemas.CardChecklistSchema(only=("title",))
    checklist_item_schema = schemas.ChecklistItemSchema()


class SIODTO:
    event_schema = schemas.SIOEventSchema()
    delete_event_scehma = schemas.SIODeleteEventSchema()
    checklist_event_schema = schemas.SIOCheckListEventSchema()
    delete_checklist_event_schema = schemas.SIOChecklistItemDeleteSchema()


class ListDTO:
    lists_schema = schemas.BoardListSchema()
    update_list_schema = schemas.BoardListSchema(exclude=("cards",))


class BoardDTO:
    board_schema = schemas.BoardSchema()
    board_query_schema = schemas.BoardQuerySchema()
    boards_schema = schemas.BoardSchema(exclude=("lists",))
    allowed_user_schema = schemas.BoardAllowedUserSchema()
    allowed_users_schema = schemas.BoardAllowedUserSchema(
        exclude=("role.permissions",))
    roles_schema = schemas.BoardRoleSchema()
