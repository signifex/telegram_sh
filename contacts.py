import json
import hashlib
import os

from typing import List, Dict, Tuple, NamedTuple, Union, Iterable, Optional, NoReturn

from . import logger
from . import CONTACTS_FILE_KEY
from .utilities import ModuleBaseException


class SendingConfigs:

    '''
    Sender-recipients configs, that class Dispatcher takes.
    API-key: Telegram bot's key.
    If value not saved in contacts file, can be set using classmethod manual_api_key(api_key)

    Name of API-key (optional), for logging.

    Recipients (Itarable object) of integers (chat id).
    If a dictionary is provided in format (int: str), the keys will be used as names for logging.
    In other cases names will have "None" values

    Only obj.api_key_name can be changed.
    '''

    class CreatingError(ModuleBaseException):
        def __init__(self, *args):
            super().__init__(*args, error_name = "Configurations for sending are not set")


    def __init__(self,
                 api_key: str,
                 recipients: Iterable[int],
                 api_key_name: Optional[str] = None):

        self._api_key = api_key
        self.api_key_name = api_key_name
        self._recipients = recipients.copy() if isinstance(recipients, dict) else dict.fromkeys(recipients)

        logging.info(f"Data for sending messages is formed, amount of recipients: {len(self._recipients)}")


    def _get_api_key(self) -> Tuple[str, str]:
        return self._api_key, self.api_key_name

    api_key = property(_get_api_key)


    def _get_recipients(self) -> Dict:
        return self._recipients

    recipients = property(_get_recipients)


    def manual_api_key(self, new_api_key: str):
        '''
        Provide API-key value manually.
        Will raise an error, if value of API-key is already set.
        '''
        if api_key:
            error = f"Replacing an existing api-key is not possible"
            raise AttributeError(error)

        else:
            self._api_key = new_api_key

        logging.info("Using manual provided api-key")
        return self


    def add_recipients(self,
                       recipients: Iterable[str],
                       overwrite_names: bool = False):

        if isinstance(recipients, dict) and overwrite_names:
            self._recipients.update(recipients)

        else:
            for recipient in recipients:
                self._recipients.setdefault(recipients)

        logging.info("Recipients list updated")
        return self



class ContactsFile:

    '''
    Class to wotk with contacts file.
    There are two main functions:

    ContactsFile.AddContacts.from_messages(api_key)
    to parce incoming messages and extract values into contacts file

    ContactsFile.create_sending_configs(searching_names, searching_bulk_groups)
    to create configs object for Dispatcher

    Also Copy subclass provides function to encrypt and decrypt contacts file, if you want to check the file manually
    '''

    _name = ".tgsend.contacts"
    _directory = os.path.dirname(os.path.realpath(__file__))
    _path = os.path.join(_directory, _name)

    _structure = {
        "default": None,
    }

    _key_structure = {
        "api_key": None,
        "contacts": {},
        "bulk_groups": {},
        "default": None
    }

    RESERVED_NAMES = set(_structure).union(_key_structure)


    class FileCorruptedError(ModuleBaseException):
        def __init__(self, *args):
            super().__init__(*args, error_name = "File corrupted")


    class ReservedValueError(ModuleBaseException):
        def __init__(self, *args):
            error_name = "Invalid value error, these values are reserved: " + ", ".join(ContactsFile.RESERVED_NAMES)
            super().__init__(self, *args, error_name = error_name)


    class Copy:

        class DecryptionError(ModuleBaseException):
            def __init__(self, *args):
                super().__init__(*args, error_name = "Decryption error")


        class EncryptionError(ModuleBaseException):
            def __init__(self, *args):
                super().__init__(*args, error_name = "Encryption error")

        @classmethod
        def decrypt(cls,
                    file_path: Optional[str] = "tgsend.contacts.decrypted",
                    file_key: Optional[bytes] = CONTACTS_FILE_KEY,
                    force_mode: Optional[bool] = False,
                    )-> NoReturn:

            contact_file = ContactsFile._load(file_key = file_key)

            mode = "w" if force_mode else "x"

            try:
                with open(file_path, mode = mode) as copy:
                    json.dump(contact_file, copy)

            except FileExistsError as e:
                 error_message = f"File '{file_path}' already exists. Use force mode to overwrite."
                 raise cls.DecryptionError(e, error_message = error_message) from e

            except IOError as e:
                raise cls.DecryptionError(e) from e

            finally:
                logging.info("File decrypted")

        @classmethod
        def encrypt(cls,
                    file_path: str,
                    file_key: Optional[bytes] = CONTACTS_FILE_KEY
                    ) -> NoReturn:

            try:
                with open(file_path, "r") as copy:
                    contact_file = json.load(copy)
                ContactsFile._save(contact_file, file_key = file_key)

            except (FileNotFoundError, IOError, json.JSONDecodeError) as e:
                raise cls.EncryptionError(e) from e

            finally:
                logging.info("File encrypted")

    class Edit:

        '''
        Edit contacts file

        '''

        class EditingError(ModuleBaseException):
            def __init__(self, original_exception):
                super().__init__(original_exception, "File editing error")


        def add_api_key(api_key_name: str,
                        api_key: Optional[str] = None,
                        file_key: Optional[bytes] = CONTACTS_FILE_KEY,
                        set_default: Optional[bool] = False,
                        force_mode: Optional[bool] = False,
                        autoconfirm: Optional[bool] = False,
                        ) -> NoReturn:

            contacts_dict = ContactsFile._load()

            if api_key_name in ContactsFile.RESERVED_NAMES:
                raise EditingError(ContactsFile.ReservedValueError)

            if not force_mode:

                if api_key_name in contacts_dict:
                    error = "API-key with this name already exists, use force-mode to overwrite"
                    raise EditingError(error)

                elif api_key is None:
                    error = "API-key is not provided, use force mode to save key without value"
                    raise EditingError(error)

                Utilities.Checkers.check_api_key(api_key = api_key)

            if api_key is None and not autoconfirm:

                while True:
                    action = input("Save empty API-key? (y/N)")

                    if not action or action.lower() == "n":
                        error = "Operation aborted by user"
                        raise EditingError(error)

                    elif action.lower() == "y":
                        break

            contacts_dict[api_key_name] = ContactsFile._key_structure
            contacts_dict[api_key_name]["api_key"] = api_key

            if set_default:
                contacts_dict["default"] = api_key_name

            cls._save(contacts_dict)

            api_is_none = ", the key value is empty" if api_key is None else ""
            is_default = ", the key set as default" if set_default else ""
            logging.info(f"api-key '{api_key_name}' saved" + api_is_none + is_default)


    class CreatingError(ModuleBaseException):
        def __init__(self, *args):
            super().__init__(*args, error_name = "File creating failed")

    @classmethod
    def create(cls,
               api_key_name: str,
               api_key: Optional[str] = None,
               file_key: Optional[bytes] = CONTACTS_FILE_KEY,
               set_default: Optional[bool] = True,
               force_mode: Optional[bool] = False,
               autoconfirm: Optional[bool] = False
               ) -> NoReturn:

        cls._check_reserved_values(api_key_name)

        if not api_key and not force_mode:
            error = "Empty api-key value. Use force-mode to save leer value, or provide valid API-key"
            raise cls.FileCreatingError(error)

        contacts_dict = cls._structure
        contacts_dict[api_key_name] = cls._key_structure

        if set_default:
            contacts_dict["default"] = api_key_name

        contacts_dict[api_key_name]["api_key"] = api_key

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

            cls._save(contacts_dict)

            print("Contacts file successfully created")

        except (ReservedValueError, FileExistsError) as e:
            raise CreatingError(e) from e

        except KeyboardInterrupt:
            raise CreatingError("Operation aborted by user")


    class LoadingError(ModuleBaseException):
        def __init__(self, *args):
            super().__init__(*args, error_name = "File not loaded")

    @classmethod
    def _load(cls, file_key = CONTACTS_FILE_KEY) -> Dict:

        try:

            with open(cls._path, mode = "rb") as file:
                binary_data = file.read()

            encrypted_data = binary_data[:-64]

            stored_hash = binary_data[-64:]

            new_hash = hashlib.sha256(encrypted_data).hexdigest().encode()

            if new_hash != stored_hash:
                error = f"file {cls._name} corrupted"
                raise FileCorruptedError(error)

            decrypted_data = bytearray(byte ^ file_key for byte in encrypted_data)

            contacts_dict = json.loads(decrypted_data.decode())

            return contacts_dict

        except (cls.FileCorruptedError, FileNotFoundError, json.JSONDecodeError) as e:
            raise LoadError(e)


    class SavingError(ModuleBaseException):
        def __init__(self, *args):
            super().__init__(*args, error_name = "File not saved")

    @classmethod
    def _save(cls,
              new_file: dict,
              file_key: bytes = CONTACTS_FILE_KEY
              ) -> NoReturn:

        json_data = json.dumps(new_file)

        encrypted_data = bytearray(byte ^ file_key for byte in json_data.encode())

        new_hash = hashlib.sha256(encrypted_data).hexdigest().encode()

        export_data = encrypted_data + new_hash

        with open(cls._path, "wb") as file:
            file.write(export_data)

    @classmethod
    def _check_reserved_values(cls, *args: str):
        error = [arg for arg in args if arg in cls.RESERVED_NAMES]
        if error:
            error_message = "provided invalid values: " + ", ".join(*error)
            raise cls.ReservedValueError(error_message)


    @classmethod
    def show_contacts(cls, api_key_name: str) -> NoReturn:

        contacts_dict = cls._load()

        api_keys = [key for key in contacts_dict.keys() if key != "default"]

        if api_keys == 0:
            message = f"no api-keys in contacts file"
            raise ValueError(message)

        elif api_key_name not in api_keys:
            message = f"api-key '{api_key_name}' not found, avalibale presented keys:\n{api_keys}"
            raise ValueError(message)

        elif contacts_dict[api_key_name]["contacts"] == {}:
            message = f"no contacts to ’{api-key}’ found"
            raise ValueError(message)

        else:
            contacts = contacts_dict[api_key_name]["contacts"].keys()
            print(*contacts)

    @classmethod
    def create_sending_configs(cls,
                               api_key_name: str,
                               api_key: str = None,
                               chat_name: Union[str, Iterable[str]] = None,
                               bulk_group: Union[str, Iterable[str]] = None,
                               manual_id: Union[int, Iterable[int]] = None,
                               ) -> SendingConfigs:

        '''
        read contacts file for chat id accoring gived names and return a SendingCofigs object.

        '''
        contacts_dict = cls._load()

        if api_key_name not in contacts_dict.keys():
            error = "name of api-key not found in  contacts file"
            raise SendingConfigs.CreatingError(error)

        elif api_key is not None:
            saved_api_key = contacts_dict[api_key_name][api_key]
            if saved_api_key != "":
                error = f"another api-key saved to by name '{api_key_name}'"
                raise SendingConfigs.CreatingError(error)

        elif all(arg is None for arg in (chat_name, bulk_group, manual_id)):
            error = "No recipients specified"
            raise SendingConfigs.CreatingError(error)

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



class GetContacts:


    class Message(NamedTuple):
        chat_id: int
        username: str
        first_name: str
        text: str


    class GetContactsError(ModuleBaseException):
        def __init__(self, *args):
            super().__init__(*args)


    def from_updates(api_key_name: str,
                     api_key: str = None,
                     filter_username: str = None,
                     filter_text: str = None) -> NoReturn:

        contacts_dict = ContactsFile._load()

        if api_key_name not in contacts_dict:
            error = f"api-key '{api_key_name}' is not exists in contacts file"
            raise GetContacts.GetContactsError(error_message = error)

        if api_key is not None:
            api_key = contacts_dict[api_key_name]["api_key"]
            logging.info("Api key taken from contacs file")

        Utilities.Checkers.check_api_key(api_key)


    def _get_updates(api_key: str) -> List:

        logging.info("Getting updates from Telagram server")

        url = f'https://api.telegram.org/bot{api_key}/getUpdates'

        with urllib.request.urlopen(url) as response_raw:
            response = json.loads(response_raw.read())

        if not response.get("ok"):
            error = "Wrong API-call"
            raise  (error)

        elif response["result"] == []:
            error = "no updates, send some message to bot, and try again"
            raise GetContacts.GetContactsError(error)

        logging.info("Returing data from Telegram server")

        return response["result"]


    def _format_messages(messages: list[Message]) -> list[Message]:

        '''
        get "result" friom Telagram, extact values and form Message class from each message
        '''
        logging.info("Messages formating starts")

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

        logging.info(f"returning {len(formated_messages)} messages")
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
        logging.info(f"Start filtering messages, filter by username: {filter_username}, filter by text: {filter_text}")

        filtered_messages = []

        for message in messages:

            if message.chat_id in existing_chat_id:
                logging.info(f"{message.chat_id} already in contacts file")
                continue

            elif filter_text != None and message.text != filter_text:
                logging.info(f"{message.text} from {message.username}({message.chat_id}) not matches to {filter_text}")
                continue

            elif filter_username != None and message.username not in (filter_username, "NOUSERNAME"):
                logging.info(f"{message.username}({message.chat_id}) not matches to {filter_username}")
                continue

            else:
                filtered_messages.append(message)

        logging.info(f"returning {len(filtered_messages)} filtered messages")

        return filtered_messages


    def _check_messages(messages: list[Message], existing_contacts: Dict[str, int]) -> NoReturn:

        logging.info("starting checking of messages")

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


