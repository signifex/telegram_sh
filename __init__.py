import logging
import configparser
import os


_configs_file_name = "configs.ini"
_directory = os.path.dirname(os.path.realpath(__file__))
_configs_file_path = os.path.join(_directory, _configs_file_name)
_config = configparser.ConfigParser()
_config.read(_configs_file_path)

CONTACTS_FILE_KEY = config["keys"]["contacts_file_key"]


logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

from .main import Handler
from .dispatcher import Dispatcher
from .contacts import ContactsFile

