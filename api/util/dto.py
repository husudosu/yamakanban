from api.util import schemas


class CardDTO:
    card_schema = schemas.CardSchema()
    update_card_schema = schemas.CardSchema(exclude=("activities",))

    comment_schema = schemas.CardCommentSchema()

    activity_schema = schemas.BoardActivitySchema()
    activity_paginated_schema = schemas.BoardActivityPaginatedSchema()
    activity_schema_query = schemas.BoardActivityQuerySchema()

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
    list_query_schema = schemas.ArchivableEntityQuerySchema()


class BoardDTO:
    board_schema = schemas.BoardSchema()
    board_query_schema = schemas.ArchivableEntityQuerySchema()
    boards_schema = schemas.BoardSchema(exclude=("lists",))
    allowed_user_schema = schemas.BoardAllowedUserSchema()
    allowed_users_schema = schemas.BoardAllowedUserSchema(
        exclude=("role.permissions",))
    roles_schema = schemas.BoardRoleSchema()
    archived_entities_query_schema = schemas.ArchivedEntititiesQuerySchema()

    archived_cards_schema = schemas.CardSchema(only=(
        "id", "title", "archived_on", "archived", "board_list.title", "board_list.id", "board_list.archived",))
    archived_lists_schema = schemas.BoardListSchema(only=(
        "id", "title", "archived_on", "cards.id", "cards.title",
    ))


class UserDTO:
    user_schema = schemas.UserSchema()
    register_schema = schemas.UserSchema(
        partial=("username", "password", "email",),
        exclude=("roles",)
    )
    update_user_schema = schemas.UserSchema(
        partial=("username", "password", "email",),
        exclude=("roles",)
    )
    update_user_schema_admin = schemas.UserSchema(
        partial=True, exclude=("current_password",))
    guest_user_schema = schemas.UserSchema(
        only=(
            "id", "username", "name",
            "avatar_url", "timezone",
            "roles",
        )
    )
    reset_password_schema = schemas.ResetPasswordSchema()
    login_schema = schemas.LoginSchema()
