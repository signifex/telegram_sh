import logging as _logging
_logging.basicConfig(level=_logging.WARNING)
logger = _logging.getLogger(__name__)

from .dispatcher import Dispatcher
from .contacts import (ContactsCreate,
                       ContactsEdit,
                       ContactsCopy,
                       ContactsGet,
                       ContactsShow,
                       CreateDispatcher
                       )

