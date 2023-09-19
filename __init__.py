import logging
import configparser
import os

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

from .main import Handler
from .dispatcher import Dispatcher
from .contacts import ContactsCreate, ContactsEdit, ContactsCopy, ContactsGet
