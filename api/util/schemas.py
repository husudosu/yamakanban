from urllib.parse import urlencode

from flask import request
from marshmallow import (Schema, ValidationError,
                         fields, validate, validates_schema, EXCLUDE)
from marshmallow_sqlalchemy import SQLAlchemySchema

from api.model.board import (
    Board, BoardAllowedUser, BoardRole, BoardRolePermission
)
from api.model.card import Card, CardComment, CardDate
from api.model.checklist import ChecklistItem, CardChecklist
from api.model.list import BoardList
from api.model import user


class PaginatedSchema(Schema):

    class Meta:
        ordered = True

    links = fields.Method(serialize='get_pagination_links')

    page = fields.Integer(dump_only=True)
    pages = fields.Integer(dump_only=True)

    per_page = fields.Integer(dump_only=True)
    total = fields.Integer(dump_only=True)

    @staticmethod
    def get_url(page):

        query_args = request.args.to_dict()
        query_args['page'] = page
        return '{}?{}'.format(request.base_url, urlencode(query_args))

    def get_pagination_links(self, paginated_objects):
        paginated_links = {
            'first': self.get_url(page=1),
            'last': self.get_url(page=paginated_objects.pages)
        }

        if paginated_objects.has_prev:
            paginated_links['prev'] = self.get_url(
                page=paginated_objects.prev_num)
        if paginated_objects.has_next:
            paginated_links['next'] = self.get_url(
                page=paginated_objects.next_num)
        return paginated_links


class PaginatedQuerySchema(Schema):
    page = fields.Integer(missing=1)
    per_page = fields.Integer(missing=15)
    sort_by = fields.String()
    order = fields.String(validate=validate.OneOf(("asc", "desc",)))


class ResetPasswordSchema(Schema):
    reset_token = fields.String(required=True, load_only=True)
    password = fields.String(required=True, load_only=True)


class UserSchema(SQLAlchemySchema):

    id = fields.Integer(dump_only=True)
    username = fields.String(validate=validate.Length(3, 255), required=True)
    name = fields.String(allow_none=True)
    avatar_url = fields.String(required=False, allow_none=True)
    password = fields.String(
        validate=validate.Length(3, 255), required=True, load_only=True)
    current_password = fields.String(
        required=True, load_only=True)

    email = fields.Email(required=True)

    registered_date = fields.DateTime(dump_only=True)

    current_login_at = fields.DateTime(dump_only=True)
    current_login_ip = fields.String(dump_only=True)
    last_login_at = fields.DateTime(dump_only=True)
    last_login_ip = fields.String(dump_only=True)

    # TODO Need a vaildator for this!
    timezone = fields.String()
    roles = fields.Method("get_roles", "get_roles_deserialize")

    def get_roles(self, data):
        return [role.name for role in data.roles]

    def get_roles_deserialize(self, obj):
        return obj

    @validates_schema
    def validate_schema(self, data, **kwargs):
        errors = {}
        # Check if user exists
        if "username" in data.keys():
            q = user.User.query.filter(
                user.User.username == data["username"])

            if self.instance:
                q = q.filter(user.User.id != self.instance.id)
            if q.first():
                errors["username"] = ["Username already taken."]
        if "email" in data.keys():
            q = user.User.query.filter(user.User.email == data["email"])

            if self.instance:
                q = q.filter(user.User.id != self.instance.id)

            if q.first():
                errors["email"] = ["Email already taken."]
        if "current_password" in data.keys():
            if not self.instance.check_password(data["current_password"]):
                errors["current_password"] = ["Invalid current password"]

        if len(errors.keys()) > 0:
            raise ValidationError(errors)

    class Meta:
        model = user.User
        unknown = EXCLUDE


class BoardListSchema(SQLAlchemySchema):

    id = fields.Integer(dump_only=True)
    board_id = fields.Integer()
    title = fields.String(required=True)
    position = fields.Integer()

    archived = fields.Boolean(dump_only=True)
    archived_on = fields.DateTime("%Y-%m-%d %H:%M:%S", dump_only=True)

    cards = fields.Nested(
        lambda: CardSchema,
        many=True,
        only=("id", "title", "position", "list_id",
              "assigned_members", "dates", "checklists.title", "checklists.items.completed", "checklists.items.id"),
        dump_only=True
    )

    class Meta:
        model = BoardList
        unknown = EXCLUDE


class BoardSchema(SQLAlchemySchema):

    id = fields.Integer(dump_only=True)
    owner_id = fields.Integer()
    title = fields.String(required=True)
    lists = fields.Nested(BoardListSchema, many=True, dump_only=True)
    background_image = fields.String()
    background_color = fields.String()

    archived = fields.Boolean(dump_only=True)
    archived_on = fields.DateTime("%Y-%m-%d %H:%M:%S", dump_only=True)

    class Meta:
        model = Board


class ArchivableEntityQuerySchema(Schema):
    archived = fields.Boolean(missing=False)


class BoardRolePermissionSchema(SQLAlchemySchema):
    id = fields.Integer(dump_only=True)
    name = fields.String(dump_only=True)
    allow = fields.Boolean()

    class Meta:
        model = BoardRolePermission


class BoardRoleSchema(SQLAlchemySchema):
    id = fields.Integer(dump_only=True)
    board_role_id = fields.Integer(dump_only=True)
    name = fields.String()
    is_admin = fields.Boolean(load_default=False)
    permissions = fields.Nested(
        BoardRolePermissionSchema, many=True, dump_only=True)

    class Meta:
        model = BoardRole


class BoardAllowedUserSchema(SQLAlchemySchema):
    id = fields.Integer(dump_only=True)
    user_id = fields.Integer(required=True)
    board_id = fields.Integer()
    board_role_id = fields.Integer(required=True)
    is_owner = fields.Boolean(dump_only=True)
    role = fields.Nested(BoardRoleSchema, dump_only=True)
    user = fields.Nested(UserSchema, only=(
        "username", "name", "avatar_url",), dump_only=True)
    is_deleted = fields.Boolean(dump_only=True)

    class Meta:
        model = BoardAllowedUser


class CardMemberSchema(SQLAlchemySchema):
    id = fields.Integer(dump_only=True)
    board_user_id = fields.Integer(required=True)
    send_notification = fields.Boolean(missing=True)

    board_user = fields.Nested(
        BoardAllowedUserSchema(only=("user", "id",)),
        dump_only=True
    )


class CardCommentSchema(SQLAlchemySchema):
    id = fields.Integer(dump_only=True)
    user_id = fields.Integer(dump_only=True)
    # activity_id = fields.Integer(dump_only=True, required=True)
    comment = fields.String(required=True)

    created = fields.DateTime(dump_only=True)
    updated = fields.DateTime(dump_only=True)

    class Meta:
        model = CardComment


class BoardActivitySchema(SQLAlchemySchema):
    id = fields.Integer(dump_only=True)
    card_id = fields.Integer()
    board_id = fields.Integer()
    board_user_id = fields.Integer()
    activity_on = fields.DateTime("%Y-%m-%d %H:%M:%S")
    entity_id = fields.Integer()
    event = fields.String(dump_only=True)

    changes = fields.String(dump_only=True)

    comment = fields.Nested(CardCommentSchema, dump_only=True)
    member = fields.Nested(CardMemberSchema, dump_only=True)

    board_user = fields.Nested(
        BoardAllowedUserSchema(only=("user", "id",)),
        dump_only=True
    )


class BoardActivityPaginatedSchema(PaginatedSchema):
    data = fields.Nested(
        BoardActivitySchema(),
        attribute="items",
        many=True
    )


class BoardActivityQuerySchema(PaginatedQuerySchema):
    type = fields.String(
        validate=validate.OneOf(["all", "comment"]), missing="comment")

    dt_from = fields.DateTime("%Y-%m-%d %H:%M:%S")
    dt_to = fields.DateTime("%Y-%m-%d %H:%M:%S")
    board_user_id = fields.Integer()

    @validates_schema
    def validate_schema(self, data, **kwargs):
        errors = {}
        if "dt_from" in data.keys() and "dt_to" in data.keys() and data["dt_from"] > data["dt_to"]:
            errors["dt_to"] = ["Can't be less than dt_from!"]
            errors["dt_from"] = ["Can't be greater than dt_to!"]

        if len(errors.keys()) > 0:
            raise ValidationError(errors)


class ChecklistItemSchema(SQLAlchemySchema):
    id = fields.Integer(dump_only=True)
    checklist_id = fields.Integer(dump_only=True)
    marked_complete_board_user_id = fields.Integer(dump_only=True)
    assigned_board_user_id = fields.Integer(allow_none=True)

    title = fields.String(required=True)
    due_date = fields.DateTime("%Y-%m-%d %H:%M:%S", allow_none=True)
    completed = fields.Boolean(load_default=False, allow_none=False)
    marked_complete_on = fields.DateTime(dump_only=True)
    position = fields.Integer()

    marked_complete_user = fields.Nested(
        BoardAllowedUserSchema(only=("user", "id",)),
        dump_only=True
    )
    assigned_user = fields.Nested(
        BoardAllowedUserSchema(only=("user", "id",)),
        dump_only=True
    )

    class Meta:
        model = ChecklistItem
        unknown = EXCLUDE


class CardChecklistSchema(SQLAlchemySchema):
    id = fields.Integer(dump_only=True)
    card_id = fields.Integer(dump_only=True)

    title = fields.String(allow_none=True)

    items = fields.Nested(ChecklistItemSchema, many=True, dump_only=True)

    class Meta:
        model = CardChecklist
        unknown = EXCLUDE


class CardDateSchema(SQLAlchemySchema):

    id = fields.Integer(dump_only=True)
    card_id = fields.Integer(dump_only=True)
    board_id = fields.Integer(dump_only=True)

    dt_from = fields.DateTime(
        "%Y-%m-%d %H:%M:%S", required=False, allow_none=True)
    dt_to = fields.DateTime("%Y-%m-%d %H:%M:%S", required=True)

    description = fields.String(allow_none=True)
    complete = fields.Boolean(allow_none=False, missing=False)

    @validates_schema
    def validate_schema(self, data, **kwargs):
        errors = {}
        dt_from = data.get("dt_from", getattr(self.instance, "dt_from", None))
        dt_to = data.get("dt_to", getattr(self.instance, "dt_to", None))

        if dt_from and dt_from > dt_to:
            errors["dt_to"] = ["Can't be less than dt_from!"]
            errors["dt_from"] = ["Can't be greater than dt_to!"]

        if len(errors.keys()) > 0:
            raise ValidationError(errors)

    class Meta:
        model = CardDate
        unknown = EXCLUDE


class CardSchema(SQLAlchemySchema):
    id = fields.Integer(dump_only=True)
    board_id = fields.Integer(dump_only=True)

    list_id = fields.Integer()
    title = fields.String(required=True)
    description = fields.String(allow_none=True)
    position = fields.Integer()

    archived = fields.Boolean()
    archived_on = fields.DateTime("%Y-%m-%d %H:%M:%S", dump_only=True)

    checklists = fields.Nested(CardChecklistSchema, many=True, dump_only=True)
    assigned_members = fields.Nested(
        CardMemberSchema(many=True),
        dump_only=True
    )
    dates = fields.Nested(CardDateSchema, many=True, dump_only=True)
    activities = fields.Nested(BoardActivitySchema, many=True, dump_only=True)

    class Meta:
        model = Card
        unknown = EXCLUDE


class CardQuerySchema(Schema):
    activity_count = fields.Integer(missing=50)


class SIOEventSchema(Schema):
    list_id = fields.Integer(required=True)
    card_id = fields.Integer(required=True)
    entity = fields.Dict(required=True)


class SIODeleteEventSchema(Schema):
    list_id = fields.Integer()
    card_id = fields.Integer()
    entity_id = fields.Integer(required=True)


class SIOChecklistItemDeleteSchema(SIODeleteEventSchema):
    checklist_id = fields.Integer()


class SIOCheckListEventSchema(SIOEventSchema):
    checklist_id = fields.Integer()


class ArchivedEntititiesQuerySchema(Schema):
    entity_type = fields.String(validate=validate.OneOf(("card", "list",)))


class ArchivedEntitySchema(Schema):
    id = fields.Integer()
    title = fields.String()
    archived_on = fields.DateTime("%Y-%m-%d %H:%M:%S")
