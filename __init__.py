import logging as _logging
_logging.basicConfig(level=_logging.WARNING)
logger = _logging.getLogger(__name__)

from .dispatcher import Dispatcher
from .tglogger import TgLogger
from .contacts import (ContactsCreate,
                       ContactsEdit,
                       ContactsCopy,
                       ContactsGet,
                       ContactsShow,
                       CreateDispatcher
                       )

try:
    import decorations
except ImportError:
    DECORATIONS = False
else:
    DECORATIONS = True
