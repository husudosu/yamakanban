import enum

from werkzeug.exceptions import NotFound


class BaseMixin(object):

    @classmethod
    def get_or_404(cls, id):
        m = cls.query.get(id)
        if m is None:
            raise NotFound(f"{cls.__tablename__} not exists")
        return m

    def update(self, **kw):
        for key, value in kw.items():
            if hasattr(self, key):
                setattr(self, key, value)


class BoardPermission(enum.Enum):
    CARD_EDIT = "card.edit"
    CARD_COMMENT = "card.comment"
    CARD_DELETE = "card.delete"
    CARD_ASSIGN_MEMBER = "card.assign_member"
    CARD_DEASSIGN_MEMBER = "card.deassign_member"
    CARD_ADD_DATE = "card.add_date"
    CARD_EDIT_DATE = "card.edit_date"

    LIST_CREATE = "list.create"
    LIST_EDIT = "list.edit"
    LIST_DELETE = "list.delete"

    BOARD_UPDATE = "board.update"

    CHECKLIST_CREATE = "checklist.create"
    CHECKLIST_EDIT = "checklist.edit"
    CHECKLIST_ITEM_MARK = "checklist_item.mark"

    FILE_DOWNLOAD = "file.download"
    FILE_UPLOAD = "file.upload"
    FILE_DELETE = "file.delete"


class BoardActivityEvent(enum.Enum):
    BOARD_CREATE = "board.create"
    BOARD_ARCHIVE = "board.archive"
    BOARD_CHANGE_TITLE = "board.change_title"
    BOARD_CHANGE_OWNER = "board.change-owner"
    BOARD_REVERT = "board.revert"

    MEMBER_ADD = "member.add"
    MEMBER_ACCESS_REVOKE = "member.access_revoke"
    MEMBER_DELETE = "member.delete"
    MEMBER_REVERT = "member.revert"
    MEMBER_CHANGE_ROLE = "member.change_role"

    LIST_CREATE = "list.create"
    LIST_UPDATE = "list.update"
    LIST_ARCHIVE = "list.archive"
    LIST_REVERT = "list.revert"
    LIST_DELETE = "list.delete"


class CardActivityEvent(enum.Enum):
    CARD_ASSIGN_TO_LIST = "card.create"
    CARD_MOVE_TO_LIST = "card.move"
    CARD_COMMENT = "card.comment"
    CARD_ARCHIVE = "card.archive"
    CARD_REVERT = "card.revert"

    CHECKLIST_CREATE = "checklist.create"
    CHECKLIST_UPDATE = "checklist.update"
    CHECKLIST_DELETE = "checklist.delete"
    CHECKLIST_ITEM_MARKED = "checklist.item.marked"

    CARD_ASSIGN_MEMBER = "card.member.assign"
    CARD_DEASSIGN_MEMBER = "card.member.deassign"
    CARD_ADD_DATE = "card.date.create"
    CARD_EDIT_DATE = "card.date.update"
    CARD_DELETE_DATE = "card.date.delete"

    FILE_UPLOAD = "file.upload"
    FILE_DELETE = "file.delete"
