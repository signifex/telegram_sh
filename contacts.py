import json
import hashlib
import os
import configparser
import pprint

from typing import List, Dict, Tuple, NamedTuple, Literal, Union, Iterable, Optional, NoReturn

from . import logger
from .utilities import ModuleBaseException, SendingConfigs, Checkers

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
    _module_directory = os.path.dirname(os.path.realpath(__file__))
    _configs_file_path = os.path.join(_module_directory, _configs_file_name)
    _contacts_file_path = os.path.join(_module_directory, _contacts_file_name)

    configurations = configparser.ConfigParser()
    configurations.read(_configs_file_path)

    _DEFAULT_FILE_KEY = configurations["keys"]["default_file_key"]

    _RESERVED_NAMES = set(_file_structure).union(key_structure)
    _PLATFORMS = ["telegram"]

    class FileSavingError(ModuleBaseException):
        def __init__(self, *args, **kwargs):
            super().__init__(error_title = "File not saved", *args, **kwargs)

    class FileLoadingError(ModuleBaseException):
        def __init__(self, *args, **kwargs):
            super().__init__(error_title = "File not loaded", *args, **kwargs)

    class FileCorruptedError(ModuleBaseException):
        def __init__(self, *args, **kwargs):
            super().__init__(error_title = "File corrupted", *args, **kwargs)

    class ReservedValueError(ModuleBaseException):
        def __init__(self, *args, **kwargs):
            error_title = "Invalid value, these values are reserved: " + ", ".join(_RESERVED_NAMES)
            super().__init__(error_title = error_title, *args, **kwargs)


    @classmethod
    def _save_file(cls,
                   new_file: dict,
                   **kwargs) -> NoReturn:

        logger.debug("Saving function started.")

        binary_data = json.dumps(new_file).encode()
        encrypted_data = cls._xor_exchange(binary_data, **kwargs)
        force_mode = kwargs.pop("force_mode", False)
        open_mode = "wb" if force_mode else "xb"

        try:
            with open(cls._contacts_file_path, mode = open_mode) as file:
                file.write(encrypted_data)

            logger.debug("Saving function completed successfully.")

        except FileExistsError as e:
            logger.error(f"An error occurred during saving: {e}")
            raise cls.FileSavingError(e) from e


    @classmethod
    def _load_file(cls,
                   file_path: Optional[str] = _contacts_file_path,
                   **kwargs) -> Dict:

        logger.debug(f"Loading of {file_path} started")

        try:

            with open(file_path, mode = "rb") as file:
                binary_data = file.read()

            decrypted_data = cls._xor_exchange(binary_data, **kwargs)
            contacts_dict = json.loads(decrypted_data.decode())

            logger.debug(f"Loading of {file_path} completed successfully.")
            return contacts_dict

        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"An error occurred during loading: {e}")
            raise cls.FileLoadingError(e)


    @classmethod
    def _xor_exchange(cls,
                      input_data: bytearray,
                      file_key: str = _DEFAULT_FILE_KEY
                      ) -> bytearray:

        logger.debug(f"Byte excahnge started.")

        byte_key = hashlib.sha512(file_key.encode()).digest()
        exchanged_data = b""

        for i, byte in enumerate(input_data):
            exchanged_data += bytes([byte ^ byte_key[i % len(byte_key)]])

        logger.debug(f"Byte excahnge finished.")

        return exchanged_data


    @classmethod
    def _check_reserved_values(cls, checking_list: List[str]):
        errors = [name for name in checking_list if name in cls._RESERVED_NAMES]
        if errors:
            error_message = "provided invalid values: " + ", ".join(*errors)
            raise ReservedValueError(error_message = error_message)


class ContactsCreate(_BaseContactsClass):

    class FileCreatingError(ModuleBaseException):
        def __init__(self, *args, **kwargs):
            super().__init__(error_title = "File creating failed", *args, **kwargs)

    def __new__(cls,
                platform: str,
                api_key_name: str,
                api_key_value: Optional[str] = None,
                set_default: Optional[bool] = True,
                force_mode: Optional[bool] = False,
                autoconfirm: Optional[bool] = False
                ) -> NoReturn:


        cls._check_reserved_values([platform, api_key_name])

        if not api_key_value and not force_mode:
            error_message = "Empty api-key value. Use force-mode to save leer value, or provide valid API-key"
            raise cls.FileCreatingError(error_message)

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


    class GetContactsError(ModuleBaseException):
        def __init__(self, *args, **kwargs,):
            super().__init__(*args, **kwargs, error_title = "Getting contacts error")


    def __new__(api_key_name: str,
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

    class DecryptionError(ModuleBaseException):
        def __init__(self, *args, **kwargs):
            super().__init__(error_title = "Decryption error", *args, **kwargs)

    class EncryptionError(ModuleBaseException):
        def __init__(self, *args, **kwargs):
            super().__init__(error_title = "Encryption error", *args, **kwargs)

    @classmethod
    def decrypt(cls,
                file_path: Optional[str] = None,
                force_mode: Optional[bool] = False,
                **kwargs)-> NoReturn:

        contact_file = cls._load_file(**kwargs)

        mode = "w" if force_mode else "x"

        file_path = os.path.join(cls._module_directory, "tgsend.contacts.decrypted") if not file_path else file_path

        logger.info(f"File's path will be: {file_path}")

        try:

            with open(file_path, mode = mode) as copy:
                json.dump(contact_file, copy, indent = 4)

            logger.info("Decryption successfully proceeded")

        except FileExistsError as e:
             error_message = f"File '{file_path}' already exists. Use force mode to overwrite."
             logger.error(error_message)
             raise cls.DecryptionError(e, error_message = error_message) from e

        except (PermissionError, IOError) as e:
            logger.error(e)
            raise cls.DecryptionError(e) from e


    @classmethod
    def encrypt(cls,
                file_path: str,
                force_mode: Optional[bool] = False,
                **kwargs) -> NoReturn:

        try:
            with open(file_path, "r") as copy:
                contact_file = json.load(copy)
            cls._save_file(contact_file, **kwargs)
            logger.info("File encrypted")

        except (FileNotFoundError, IOError, json.JSONDecodeError) as e:
            raise cls.EncryptionError(e) from e



class ContactsEdit(_BaseContactsClass):

    '''
    Edit contacts file

    '''

    class EditingError(ModuleBaseException):
        def __init__(self, *args, **kwargs):
            super().__init__(error_title = "File editing error", *args, **kwargs)

    @classmethod
    def add_api_key(cls,
                    platform: str,
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

    def __new__(cls) -> NoReturn:

        contacts_dict = cls._load_file()

        pp = pprint.PrettyPrinter()
        pp.pprint(contacts_dict)

        # api_key_contacts = contacts_dict.get(api_key_name, None)

        # if api_key_name not in api_keys:
        #     error_message = f"api-key '{api_key_name}' not found, avalibale presented keys:\n{api_keys}"
        #     raise ValueError(error_message)

        # elif contacts_dict[api_key_name]["contacts"] == {}:
        #     error_message = f"no contacts to ’{api-key}’ found"
        #     raise ValueError(error_message)

        # else:
        #     contacts = contacts_dict[api_key_name]["contacts"].keys()
        #     print(*contacts)


class CreateSendingConfigs(_BaseContactsClass):

    '''
    read contacts file for chat id accoring gived names and return a SendingCofigs object.

    '''

    class ConfigsCreatingError(ModuleBaseException):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs, error_title = "An error occurred during creating sending configurations")

    def __new__(cls,
                platform: str = "default",
                api_key_name: str = "default",
                chat_names: Union[str, Iterable[str]] = None,
                bulk_groups: Union[str, Iterable[str]] = None,
                manual_chats: Union[int, Iterable[int]] = None,
                found_only: bool = False,
                **kwargs) -> SendingConfigs:

        '''
        main arguments:
        platform: str - telegram/whatsapp/discord etc (currently telegram only)
        api_key_name: str - name of saved api-key (probably will add re as an option)

        recipients arguments:
        manual_chats: integer or iterable of integers(dictonaries as {int: name})
        bulk_groups: string or itarable of strings with names of bulk groups as stored
        chat_names: same as bulk_groups, but more accurate (bulk_groups are stored as sets, chat_names as dictionary)

        optional hidden arguments:
        api_key_value: str - if you dont save api_key to contacts file, you have to provide it now
        file_key: str - if use not default one.
        found_only: bool - dont raise an error, if some name of bulk_group or chat_name is not found
        '''

        deeper_kwargs = {key: kwargs[key] for key in ["file_key"] if key in kwargs}
        contacts_dict = cls._load_file(**deeper_kwargs)


        if platform not in contacts_dict:
            error_message = f"Platform '{platform}' is not found in contacts file"
            raise cls.ConfigsCreatingError(error_message = error_message)
        elif platform == "default":
            platform = contacts_dict["default"]
            logger.debug("Using default platform.")


        if api_key_name not in contacts_dict[platform]:
            error_message = f"Api-key '{api_key_name}' not found in list associated with platform '{platform}'."
            raise cls.ConfigsCreatingError(error_message = error_message)
        elif api_key_name == "default":
            api_key_name = contacts_dict[platform]["default"]
            logger.debug("Using default api-key")

        api_key_value = contacts_dict[platform][api_key_name]["api_key_value"]

        if kwargs.get("api_key_value"):

            if api_key_value:
                error_message = f"Another api-key saved to by name '{api_key_name}' and cannot be replaced."
                raise cls.CreatingConfiurationsError(error_message = error_message)
            else:
                api_key_value = kwargs["api_key_value"]


        if all(arg is None for arg in (chat_names, bulk_groups, manual_chats)):
            error_message = "No recipients specified."
            raise cls.ConfigsCreatingError(error_message = error_message)

        recipients = dict()
        not_found = []
        contacts_subdict = contacts_dict[platform][api_key_name]


        if manual_chats is not None:

            logger.debug("Adding manually provided items.")

            if isinstance(manual_chats, int):
                manual_chats = {manual_chats}
            elif isinstance(manual_chats, dict):
                recipients.update(manual_chats)
            else:
                manual_chats = dict.fromkeys(manual_chats, "manually provided")
                recipients.update(manual_chats)


        if bulk_groups is not None:

            logger.info("Adding bulk groups.")

            searching_groups = {bulk_groups} if isinstance(bulk_groups, str) else set(bulk_groups)
            existing_groups = set(contacts_subdict["bulk_groups"])

            found_groups = searching_groups.intersection(existing_groups)
            not_found_groups = searching_groups.difference(existing_groups)

            if found_groups:

                for group in found_groups:

                    adding_group = dict.fromkeys(contacts_subdict["bulk_groups"][group],
                                                 f"bulk group '{group}'")

                    overwriting_recipients = {key: f"{recipients[key]}, bulk group '{group}'"
                                              for key in adding_group.keys() & recipients.keys()}

                    recipients.update(adding_group)
                    recipients.update(overwriting_recipients)

            if not_found_groups:
                not_found.append("bulk_groups: " + ", ".join(not_found_groups))

        if chat_names is not None:

            logger.info("Adding chat names.")

            searching_chats = {chat_names} if isinstance(chat_names, str) else set(chat_names)
            existing_chats = contacts_subdict["chat_names"]

            found_chats = searching_chats.intersection(existing_chats.keys())
            not_found_chats = searching_chats.difference(existing_chats.keys())

            if found_chats:

                adding_chats = {existing_chats[name]: f"chat name '{name}'" for name in found_chats}

                overwriting_recipients = {key: f"{recipients[key]}, chat name '{name}'"
                                          for name in adding_chats.keys() & recipients.keys()}

                recipients.update(adding_chats)
                recipients.update(overwriting_recipients)


            if not_found_chats:
                not_found.append("chat_names: " + ", ".join(not_found_chats))


        if not_found:

            error_message = "These names were not found:\n" + "\n".join(not_found)

            if found_only:
                raise cls.ConfigsCreatingError(error_message = error_message)

            else:
                logger.info(error_message)
                print(error_message)

        if not recipients:
            error_message = "Recipients list is leer"
            raise cls.ConfigsCreatingError(error_message = error_message)

        return SendingConfigs(api_key_value = api_key_value, api_key_name = api_key_name, recipients = recipients)

