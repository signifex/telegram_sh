import json
import hashlib
import os
import configparser
import pprint

from typing import List, Dict, Tuple, NamedTuple, Union, Iterable, Optional, NoReturn

from . import logger
from .utilities import _ModuleBaseException, SendingConfigs, Checkers

class _BaseContactsClass:

    _file_structure = {
        "default": None,
    }

    key_structure = {
        "api_key": None,
        "contacts": {},
        "bulk_groups": {},
        "default": None
    }

    _configs_file_name = "configs.ini"
    _contacts_file_name = ".tgsend.contacts"
    _current_directory = os.path.dirname(os.path.realpath(__file__))
    _configs_file_path = os.path.join(_current_directory, _configs_file_name)
    _contacts_file_path = os.path.join(_current_directory, _contacts_file_name)

    configurations = configparser.ConfigParser()
    configurations.read(_configs_file_path)

    _DEFAULT_FILE_KEY = configurations["keys"]["default_file_key"]

    _RESERVED_NAMES = set(_file_structure).union(key_structure)


    class FileSavingError(_ModuleBaseException):
        def __init__(self, *args):
            super().__init__(*args, error_title = "File not saved")

    class FileLoadingError(_ModuleBaseException):
        def __init__(self, *args):
            super().__init__(*args, error_title = "File not loaded")

    class FileCorruptedError(_ModuleBaseException):
        def __init__(self, *args):
            super().__init__(*args, error_title = "File corrupted")

    class ReservedValueError(_ModuleBaseException):
        def __init__(self, *args):
            error_title = "Invalid value, these values are reserved: " + ", ".join(_RESERVED_NAMES)
            super().__init__(*args, error_title = error_title)


    @classmethod
    def _save_file(cls,
                   new_file: dict,
                   mode: str = "xb",
                   *args) -> NoReturn:

        logger.debug("Saving function started.")

        binary_data = json.dumps(new_file).encode()
        encrypted_data = cls._xor_exchange(binary_data, *args)

        try:
            with open(cls._contacts_file_path, mode) as file:
                file.write(encrypted_data)

            logger.debug("Saving function completed successfully.")

        except FileExistsError as e:
            logger.error(f"An error occurred during saving: {e}")
            raise cls.FileSavingError(e) from e


    @classmethod
    def _load_file(cls,
                   file_path: Optional[str] = _contacts_file_path,
                   *args) -> Dict:

        logger.debug(f"Loading of {file_path} started")

        try:

            with open(file_path, mode = "rb") as file:
                binary_data = file.read()

            decrypted_data = cls._xor_exchange(binary_data, *args)
            contacts_dict = json.loads(decrypted_data.decode())

            logger.debug("Loading of {file_path} completed successfully.")
            return contacts_dict

        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"An error occurred during loading: {e}")
            raise cls.FileLoadingError(e)


    @classmethod
    def _xor_exchange(cls,
                      input_data: bytearray,
                      file_key: str = _DEFAULT_FILE_KEY
                      ) -> bytearray:

        logger.info(f"Byte excahnge started")

        byte_key = hashlib.sha256(file_key.encode()).digest()
        exchanged_data = b""

        for i, byte in enumerate(input_data):
            exchanged_data += bytes([byte ^ byte_key[i % len(byte_key)]])

        return exchanged_data


    @classmethod
    def _check_reserved_values(cls, *args: List[str]):
        errors = [arg for arg in args if arg in cls._RESERVED_NAMES]
        if errors:
            error_message = "provided invalid values: " + ", ".join(*errors)
            raise ReservedValueError(error_message)


class ContactsCreate(_BaseContactsClass):

    class FileCreatingError(_ModuleBaseException):
        def __init__(self, *args):
            super().__init__(*args, error_title = "File creating failed")

    @classmethod
    def __call__(cls,
                 api_key_name: str,
                 api_key_value: Optional[str] = None,
                 file_key: Optional[str] = None,
                 set_default: Optional[bool] = True,
                 force_mode: Optional[bool] = False,
                 autoconfirm: Optional[bool] = False
                 ) -> NoReturn:


        cls._check_reserved_values([api_key_name])

        if manual_api_key is None:
            api_key_value = cls._DEFAULT_FILE_KEY
            logger.info("Api key taken from contacs file")
        else:
            api_key_value = manual_api_key

        if not api_key_value and not force_mode:
            error_message = "Empty api-key value. Use force-mode to save leer value, or provide valid API-key"
            raise cls.FileFileCreatingError(error_message)

        contacts_dict = cls._file_structure
        contacts_dict[api_key_name] = cls.key_structure

        if set_default:
            contacts_dict["default"] = api_key_name

        contacts_dict[api_key_name]["api_key"] = api_key_value

        try:

            if not force_mode and os.path.exists(cls._path):
                raise FileExistsError(f"file {cls._path} already exists, use force mode to overwrite or delete manually")

            if api_key is None and not autoconfirm:

                while True:
                    action = input("Save empty API-key? (y/N)")

                    if not action or action.lower() == "n":
                        raise KeyboardInterrupt

                    elif action.lower() == "y":
                        break

            cls._save_file(contacts_dict)

            print("Contacts file successfully created")

        except (ReservedValueError, FileExistsError) as e:
            raise FileCreatingError(e) from e

        except KeyboardInterrupt:
            raise FileCreatingError("Operation aborted by user")


class ContactsGet(_BaseContactsClass):


    class Message(NamedTuple):
        chat_id: int
        username: str
        first_name: str
        text: str


    class GetContactsError(_ModuleBaseException):
        def __init__(self, *args):
            super().__init__(*args)


    def __call__(api_key_name: str,
                 manual_api_key: str = None,
                 filter_username: str = None,
                 filter_text: str = None
                 ) -> NoReturn:

        contacts_dict = ContactsFile._load_file()

        if api_key_name not in contacts_dict:
            error = f"api-key '{api_key_name}' is not exists in contacts file"
            raise GetContacts.GetContactsError(error_message = error)

        if manual_api_key is not None:
            api_key = _DEFAULT_FILE_KEY
            logger.info("Api key taken from contacs file")
        else:
            api_key = manual_api_key

        Chechers.check_api_key(api_key)


    def _get_updates(api_key: str) -> List:

        logger.info("Getting updates from Telagram server")

        url = f'https://api.telegram.org/bot{api_key}/getUpdates'

        with urllib.request.urlopen(url) as response_raw:
            response = json.loads(response_raw.read())

        if not response.get("ok"):
            error = "Wrong API-call"
            raise  (error)

        elif response["result"] == []:
            error = "no updates, send some message to bot, and try again"
            raise GetContacts.GetContactsError(error)

        logger.info("Returing data from Telegram server")

        return response["result"]


    def _format_messages(messages: list[Message]) -> list[Message]:

        '''
        get "result" friom Telagram, extact values and form Message class from each message
        '''
        logger.info("Messages formating starts")

        formated_messages_dict = {}

        for message in messages:

            shortcut = message["message"]["from"]

            chat_id = shortcut["id"]
            username = shortcut.get("username", "NOUSERNAME")
            first_name = shortcut.get("first_name", "NOFIRSTNAME")
            text = message["message"].get("text", "")

            '''
            formated_messages_dict[chat_id] = Message(chat_id=chat_id, username=username, first_name=first_name, text=text)
            should be modified to use formated_messages_dict[chat_id] as the key inside the NamedTuple.
            It should be formated_messages_dict[chat_id] = Message(message.chat_id, username, first_name, text).

            '''
            formated_messages_dict[chat_id] = Message(chat_id = chat_id, username = username,
                                                      first_name = first_name, text = text)

        formated_messages = [formated_messages_dict.values()]

        logger.info(f"returning {len(formated_messages)} messages")
        return formated_messages


    def _filter_messages(messages: List[Message],
                         existing_chat_id: List[int],
                         filter_username: str = None,
                         filter_text: str = None
                         ) -> list[Message]:

        '''
        filter each Message according:
        1) not in dictionary
        2) from username
        3) contains right message
        '''
        logger.info(f"Start filtering messages, filter by username: {filter_username}, filter by text: {filter_text}")

        filtered_messages = []

        for message in messages:

            if message.chat_id in existing_chat_id:
                logger.info(f"{message.chat_id} already in contacts file")
                continue

            elif filter_text != None and message.text != filter_text:
                logger.info(f"{message.text} from {message.username}({message.chat_id}) not matches to {filter_text}")
                continue

            elif filter_username != None and message.username not in (filter_username, "NOUSERNAME"):
                logger.info(f"{message.username}({message.chat_id}) not matches to {filter_username}")
                continue

            else:
                filtered_messages.append(message)

        logger.info(f"returning {len(filtered_messages)} filtered messages")

        return filtered_messages


    def _check_messages(messages: list[Message], existing_contacts: Dict[str, int]) -> NoReturn:

        logger.info("starting checking of messages")

        existing_contacts = existing_contacts.copy()

        c_message = Colorize(text = f"There are {len(messages)} contacts to check", color = "green")
        print(c_message)

        for message in messages[:]:

            chat_id = message.chat_id
            username = message.username
            full_text = message.text
            text = (full_text[:50] + "...") if len(full_text) > 50 else full_text

            if chat_id in existing_contacts.values():
                existing_username = next(key for key, value in existing_contacts.items() if value == chat_id)
                c_message = Colorize(text=f"'{username}' already saved in contacts file as '{existing_username}', skipped", color="yellow")
                print(c_message)
                messages.remove(message)

            else:

                try:

                    contact_not_processed = True

                    while contact_not_processed:

                        action = input(f"'{username}': {text}\nAdd '{username}' (Y/n)? ")

                        if action.lower() in ("y", ""):

                            while contact_not_processed:

                                if username in existing_contacts:
                                    new_username = input(f"Enter a contact name for (name '{username}' already set to another contact):\n")

                                else:
                                    new_username = input(f"Enter a new username for '{username}' (or press Enter to keep the username):\n")
                                    new_username = username if new_username == "" else new_username

                                if len(new_username) < 3:
                                    c_message = Colorize(text = "Contact's name is too short", color = "red")
                                    print(c_message)

                                else:
                                    confirm = input(f"Add contact with username '{new_username}'? (Y/n): ")

                                    while contact_not_processed:

                                        if not confirm or confirm.lower() == "y":
                                            c_message = Colorize(text=f"Adding contact: {new_username}", color="green")
                                            existing_contacts[new_username] = message.chat_id
                                            messages.remove(message)
                                            print(c_message)
                                            contact_not_processed = False
                                            break

                                        elif confirm.lower() == "n":
                                            break

                                        else:
                                            c_message = Colorize(text = "Wrong input", color = "red")
                                            print(c_message)


                        elif action.lower() == "n":
                            c_message = Colorize(text = f"Username '{username}' skipped", color = "yellow")
                            print(c_message)
                            messages.remove(message)
                            break


                        else:
                            c_message = Colorize(text = "Wrong input", color = "red")
                            print(c_message)

                except KeyboardInterrupt:
                    messages.remove(message)
                    c_message = Colorize(text = f"\n'{username}' skipped", color = "yellow")
                    print(c_message)



class ContactsCopy(_BaseContactsClass):

    class DecryptionError(_ModuleBaseException):
        def __init__(self, *args):
            super().__init__(error_title = "Decryption error", *args)

    class EncryptionError(_ModuleBaseException):
        def __init__(self, *args):
            super().__init__(error_title = "Encryption error", *args)

    @classmethod
    def decrypt(cls,
                file_path: Optional[str] = "tgsend.contacts.decrypted",
                force_mode: Optional[bool] = False,
                *args)-> NoReturn:

        contact_file = cls._load_file()

        mode = "w" if force_mode else "x"

        try:
            with open(file_path, mode = mode) as copy:
                json.dump(contact_file, copy)

        except FileExistsError as e:
             error_message = f"File '{file_path}' already exists. Use force mode to overwrite."
             raise cls.DecryptionError(e, error_message = error_message) from e

        except IOError as e:
            raise cls.DecryptionError(e) from e


    @classmethod
    def encrypt(cls,
                file_path: str,
                force_mode: Optional[bool] = False,
                *args) -> NoReturn:

        try:
            with open(file_path, "r") as copy:
                contact_file = json.load(copy)
            cls._save_file(contact_file, *args)
            logger.info("File encrypted")

        except (FileNotFoundError, IOError, json.JSONDecodeError) as e:
            raise cls.EncryptionError(e) from e



class ContactsEdit(_BaseContactsClass):

    '''
    Edit contacts file

    '''

    class EditingError(_ModuleBaseException):
        def __init__(self, original_exception):
            super().__init__(original_exception, "File editing error")

    @classmethod
    def add_api_key(cls,
                    api_key_name: str,
                    api_key_value: Optional[str] = None,
                    file_key: Optional[bytes] = None,
                    set_default: Optional[bool] = False,
                    force_mode: Optional[bool] = False,
                    autoconfirm: Optional[bool] = False,
                    ) -> NoReturn:

        contacts_dict = cls._load_file()

        if api_key_name in _RESERVED_NAMES:
            raise EditingError(cls.ReservedValueError)

        if not force_mode:

            if api_key_name in contacts_dict:
                error = "API-key with this name already exists, use force-mode to overwrite"
                raise EditingError(error)

            elif api_key is None:
                error = "API-key is not provided, use force mode to save key without value"
                raise cls.EditingError(error)

            Checkers.check_api_key(api_key = api_key)

        if api_key is None and not autoconfirm:

            while True:
                action = input("Save empty API-key? (y/N)")

                if not action or action.lower() == "n":
                    error = "Operation aborted by user"
                    raise EditingError(error)

                elif action.lower() == "y":
                    break

        contacts_dict[api_key_name] = cls.key_structure
        contacts_dict[api_key_name]["api_key"] = api_key

        if set_default:
            contacts_dict["default"] = api_key_name

        cls._save_file(contacts_dict)

        api_is_none = ", the key value is empty" if api_key is None else ""
        is_default = ", the key set as default" if set_default else ""
        logger.info(f"api-key '{api_key_name}' saved" + api_is_none + is_default)


class ContactsShow(_BaseContactsClass):

    @classmethod
    def __call__(cls,
                 api_key_name: str) -> NoReturn:

        contacts_dict = cls._load_file()

        api_key_contacts = contacts_dict.get(api_key_name, None)

        if api_key_name not in api_keys:
            error_message = f"api-key '{api_key_name}' not found, avalibale presented keys:\n{api_keys}"
            raise ValueError(error_message)

        elif contacts_dict[api_key_name]["contacts"] == {}:
            error_message = f"no contacts to ’{api-key}’ found"
            raise ValueError(error_message)

        else:
            contacts = contacts_dict[api_key_name]["contacts"].keys()
            print(*contacts)


class CreateSendingConfigs(_BaseContactsClass):

    '''
    read contacts file for chat id accoring gived names and return a SendingCofigs object.

    '''

    def __call__(api_key_name: str,
                 api_key: str = None,
                 chat_name: Union[str, Iterable[str]] = None,
                 bulk_group: Union[str, Iterable[str]] = None,
                 manual_id: Union[int, Iterable[int]] = None,
                 ) -> SendingConfigs:

        contacts_dict = cls._load_file()

        if api_key_name not in contacts_dict.keys():
            error = "name of api-key not found in  contacts file"
            raise SendingConfigs.FileCreatingError(error)

        elif api_key is not None:
            saved_api_key = contacts_dict[api_key_name][api_key]
            if saved_api_key != "":
                error = f"another api-key saved to by name '{api_key_name}'"
                raise SendingConfigs.FileCreatingError(error)

        elif all(arg is None for arg in (chat_name, bulk_group, manual_id)):
            error = "No recipients specified"
            raise SendingConfigs.FileCreatingError(error)

        recipients = dict()
        not_found = dict()

        if bulk_group is not None:

            if isinstance(bulk_group, str):
                bulk_group = {bulk_group}

            else:
                bulk_group = set(bulk_group)

            bulk_groups = contacts_dict[api_key_name]["bulk_groups"]
            not_found["bulk_groups"] = {group for group in bulk_group if group not in bulk_groups}
            found_groups = bulk_group - not_found["bulk_groups"]
            found_groups_values = set()

            for group in found_groups:
                found_groups_values |= contacts_dict[api_key_name]["bulk_groups"][group]

            bulk_recipients = dict.fromkeys(found_groups_values)

            recipients.update(bulk_recipients)

        if manual_id is not None:
            if isinstance(manual_id, int):
                manual_id = {manual_id}
            if isinstance(manual_id, dict):
                recipients.update(manual_id)
            else:
                manual_id = dict.fromkeys(manual_id)
                recipients.update(manual_id)

        if chat_name is not None:

            if isinstance(chat_name, str):
                chat_name = {chat_name}

            contacts = contacts_dict[api_key_name]["contacts"]

            found_contacts = {value: key for key, value in contacts.items() if key in chat_name}

            not_found["contacts"] = {name for name in chat_name if name not in contacts}

            for key, value in found_contacts.items():
                recipients.setdefault(key, value)

        if not_found:
            print("These names not found:")
            for key, value in not_found.items():
                print(key, ": ", *value)

        if not contacts:
            print("Recipients list is leer")

        return SendingConfigs(api_key = api_key, api_key_name = api_key_name, recipients = recipients)

