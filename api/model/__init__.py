import enum

from werkzeug.exceptions import NotFound


class RestEnum(enum.IntEnum):
    """
    Tuple list compatibile with Restful argparse choices.
    """

    @classmethod
    def tuple(cls):
        return tuple(t.value for t in cls)


class BaseMixin(object):
    """
    BaseMixin class contains.
    """

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
    LIST_CREATE = "list.create"
    LIST_EDIT = "list.edit"
    LIST_DELETE = "list.delete"
    BOARD_UPDATE = "board.update"
    BOARD_DELETE = "board.delete"
    BOARD_INVITE_MEMBER = "board.invite_member"


class CardActivityEvent(RestEnum):
    CARD_ASSIGN_TO_LIST = 1
    CARD_MOVE_TO_LIST = 2
    CARD_COMMENT = 3
