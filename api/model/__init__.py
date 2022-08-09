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
            raise NotFound("Not exists")
        return m

    def update(self, **kw):
        for key, value in kw.items():
            if hasattr(self, key):
                setattr(self, key, value)


class BoardPermissions(enum.Enum):
    CARD = "card"
    CARD_LIST_ASSIGNMENT = "card.list.assign"
    CARD_DESCRIPTION_UPDATE = "card.list.deassign"
    CARD_COMMENT = "card.comment"
    CARD_DUE_DATE = "card.due_date"
    CARD_LABEL_ASSIGNMENT = "card.label.assign"


class CardActivityEvent(RestEnum):
    CARD_ASSIGN_TO_LIST = 1
    CARD_MOVE_TO_LIST = 2
    CARD_COMMENT = 3
