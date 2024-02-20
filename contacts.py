import json
import hashlib
import os
import ctypes
import pprint

from typing import List, Dict, Union, Iterable, Optional, NoReturn

from . import logger
from .utilities import ModuleBaseException, _CallableClassMeta, Checkers
from .dispatcher import Dispatcher


class _BaseContactsClass:

    _FILE_STRUCTURE = {
        "default_bot": None,
        "default_chat": None,
        "bots": {},
        "chat_names": {},
        "bulk_groups": {}
    }

    _CONTACTS_FILE_NAME = ".tgsend.contacts"
    _C_LIB_FILE_NAME = "tgsend.so"

    _MODULE_DIRECTORY = os.path.dirname(os.path.realpath(__file__))

    _C_LIB_FILE_PATH = os.path.join(_MODULE_DIRECTORY, _C_LIB_FILE_NAME)
    _CONTACTS_FILE_PATH = os.path.join(_MODULE_DIRECTORY, _CONTACTS_FILE_NAME)

    _RESERVED_NAMES = set(_FILE_STRUCTURE)

    class FileSavingError(ModuleBaseException):
        def __init__(self, *args, **kwargs):
            super().__init__(error_title="File not saved", *args, **kwargs)

    class FileLoadingError(ModuleBaseException):
        def __init__(self, *args, **kwargs):
            super().__init__(error_title="File not loaded", *args, **kwargs)

    class FileCorruptedError(ModuleBaseException):
        def __init__(self, *args, **kwargs):
            super().__init__(error_title="File corrupted", *args, **kwargs)

    class ReservedValueError(ModuleBaseException):
        def __init__(self, *args, **kwargs):
            error_title = "Invalid value, these values are reserved: " + \
                ", ".join(_BaseContactsClass._RESERVED_NAMES)
            super().__init__(error_title=error_title, *args, **kwargs)

    class FileNotFoundError(ModuleBaseException):
        def __init__(self, *args, **kwargs):
            super().__init__(error_title="File not found",
                             *args, **kwargs)

    class DefaultValueError(ModuleBaseException):
        def __init__(self, *args, **kwargs):
            super().__init__(error_title="Default value error",
                             *args, **kwargs)

    @classmethod
    def _save_contacts_file(cls,
                            new_file: dict,
                            force_mode: bool = False,
                            **kwargs) -> None:

        logger.debug("Saving function started.")

        binary_data = json.dumps(new_file).encode()
        encrypted_data = cls._xor_exchange(binary_data, **kwargs)
        open_mode = "wb" if force_mode else "xb"

        logger.debug("open_mode", open_mode, "force mode", force_mode)

        try:
            with open(cls._CONTACTS_FILE_PATH, mode=open_mode) as file:
                file.write(encrypted_data)

            logger.debug("Saving function completed successfully.")

        except FileExistsError as e:
            logger.error(f"An error occurred during saving: {e}")
            raise cls.FileSavingError(e) from e

    @classmethod
    def _load_contacts_file(cls,
                            file_path: Optional[str] = _CONTACTS_FILE_PATH,
                            **kwargs) -> Dict:

        logger.debug(f"Loading of {file_path} started")

        try:

            with open(file_path, mode="rb") as file:
                binary_data = file.read()

            decrypted_data = cls._xor_exchange(binary_data, **kwargs)
            contacts_dict = json.loads(decrypted_data.decode())

            logger.debug(f"Loading of {file_path} completed successfully.")
            return contacts_dict

        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"An error occurred during loading: {e}")
            raise cls.FileLoadingError(e) from e

    @classmethod
    def _xor_exchange(cls,
                      input_data: bytearray,
                      file_key: str = None
                      ) -> bytearray:

        try:
            lib = ctypes.CDLL(cls._C_LIB_FILE_PATH)
        except OSError as e:
            raise cls.FileNotFoundError(e) from e

        lib.xor_exchange.argtypes = [ctypes.POINTER(ctypes.c_ubyte),
                                     ctypes.c_size_t,
                                     ctypes.POINTER(ctypes.c_ubyte)]

        lib.xor_exchange.restype = ctypes.POINTER(ctypes.c_ubyte)

        logger.debug("Byte excahnge started.")

        if file_key:
            file_key = hashlib.sha512(file_key).digest()

        data_len = len(input_data)
        input_data_c = (ctypes.c_ubyte * data_len)(*input_data)
        result = lib.xor_exchange(input_data_c, data_len, file_key)

        exchanged_data = bytearray(result[i] for i in range(data_len))

        logger.debug("Byte excahnge finished.")

        return exchanged_data

    @classmethod
    def _check_reserved_values(cls, checking_list: List[str]):
        errors = [name for name in checking_list
                  if name in cls._RESERVED_NAMES]

        if errors:
            error_message = "provided invalid values: " + ", ".join(*errors)
            raise cls.ReservedValueError(error_message=error_message)


# class CompileEncrypter(_BaseContactsClass,
#                        metaclass=_CallableClassMeta,
#                        class_call_method="_create_contacts_file"):
#     pass


class ContactsCreate(_BaseContactsClass,
                     metaclass=_CallableClassMeta,
                     class_call_method="_create_contacts_file"):

    class FileCreatingError(ModuleBaseException):
        def __init__(self, *args, **kwargs):
            super().__init__(error_title="File creating failed",
                             *args, **kwargs)

    @classmethod
    def _create_contacts_file(cls,
                              api_key_name: str,
                              api_key_value: Optional[str] = None,
                              set_default: Optional[bool] = True,
                              force_mode: Optional[bool] = False,
                              autoconfirm: Optional[bool] = False
                              ) -> None:

        cls._check_reserved_values([api_key_name])

        if not api_key_value and not force_mode:
            error_message = "Empty api-key value. Use force-mode" \
                "to save a leer key value, or provide valid API-key"
            raise cls.FileCreatingError(error_message)

        contacts_dict = cls._FILE_STRUCTURE
        contacts_dict[api_key_name] = cls.__KEY_TEMPLATE

        if set_default:
            contacts_dict["default"] = api_key_name

        contacts_dict[api_key_name]["api_key"] = api_key_value

        try:

            if not force_mode and os.path.exists(cls._path):
                error_message = f"file {cls._path} already exists, " \
                    "use force mode to overwrite or delete manually"
                raise FileExistsError(error_message=error_message)

            if api_key_value is None and not autoconfirm:

                while True:
                    action = input("Save empty API-key? (y/N)")

                    if not action or action.lower() == "n":
                        raise KeyboardInterrupt

                    elif action.lower() == "y":
                        break

            cls._save_contacts_file(contacts_dict)

            print("Contacts file successfully created")

        except (cls.ReservedValueError, FileExistsError) as e:
            raise cls.FileCreatingError(e) from e

        except KeyboardInterrupt:
            raise cls.FileCreatingError("Operation aborted by user")


class ContactsGet(_BaseContactsClass,
                  metaclass=_CallableClassMeta,
                  class_call_method="_get_updates"):

    # @dataclass
    class Message:
        chat_id: int
        username: str
        first_name: str
        text: str

    class GetContactsError(ModuleBaseException):
        def __init__(self, *args, **kwargs,):
            super().__init__(error_title="Getting contacts error",
                             *args, **kwargs)

    @classmethod
    def _get_updates(cls,
                     api_key_name: str,
                     manual_api_key: str = None,
                     filter_username: str = None,
                     filter_text: str = None
                     ) -> NoReturn:

        contacts_dict = cls._load_contacts_file()

        if api_key_name not in contacts_dict:
            error_message = f"api-key '{api_key_name}' " \
                "is not exists in contacts file"
            raise cls.GetContactsError(error_message=error_message)

        if manual_api_key is not None:
            logger.info("Api key taken from contacs file")
        else:
            api_key = manual_api_key

        Checkers.check_api_key(api_key)


    # def _get_updates(api_key: str) -> List:

    #     logger.info("Getting updates from Telagram server")

    #     url = f'https://api.telegram.org/bot{api_key}/getUpdates'

    #     with urllib.request.urlopen(url) as response_raw:
    #         response = json.loads(response_raw.read())

    #     if not response.get("ok"):
    #         error = "Wrong API-call"
    #         raise  (error)

    #     elif response["result"] == []:
    #         error = "no updates, send some message to bot, and try again"
    #         raise GetContacts.GetContactsError(error)

    #     logger.info("Returing data from Telegram server")

    #     return response["result"]

    @classmethod
    def _format_messages(cls, messages: list[Message]) -> list[Message]:
        '''
        get "result" from Telagram, extact values and form
        Message class from each message
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
            formated_messages_dict[chat_id] =
            Message(chat_id, username, first_name, text)

            should be modified to use formated_messages_dict[chat_id]
            as the key inside the NamedTuple.
            It should be formated_messages_dict[chat_id] =
            Message(message.chat_id, username, first_name, text).

            '''
            formated_messages_dict[chat_id] = cls.Message(chat_id=chat_id,
                                                          username=username,
                                                          first_name=first_name,
                                                          text=text)

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
        logger.info("Start filtering messages, filter by username: "
                    f"{filter_username}, filter by text: {filter_text}")

        filtered_messages = []

        for message in messages:

            if message.chat_id in existing_chat_id:
                logger.info(f"{message.chat_id} already in contacts file")
                continue

            elif filter_text is not None and message.text != filter_text:
                logger.info(f"{message.text} from {message.username} ({message.chat_id}) not matches to {filter_text}")
                continue

            elif filter_username is not None and message.username not in (filter_username, "NOUSERNAME"):
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
            super().__init__(error_title="Decryption error",
                             *args, **kwargs)

    class EncryptionError(ModuleBaseException):
        def __init__(self, *args, **kwargs):
            super().__init__(error_title="Encryption error",
                             *args, **kwargs)

    @classmethod
    def decrypt(cls,
                file_path: Optional[str] = None,
                force_mode: Optional[bool] = False,
                **kwargs)-> NoReturn:

        contact_file = cls._load_contacts_file(**kwargs)

        mode = "w" if force_mode else "x"

        file_path = os.path.join(cls._MODULE_DIRECTORY, "tgsend.contacts.decrypted") if not file_path else file_path

        logger.info(f"File's path will be: {file_path}")

        try:

            with open(file_path, mode = mode) as copy:
                json.dump(contact_file, copy, indent = 4)

            logger.info("Decryption successfully proceeded")

        except FileExistsError as e:
            error_message = f"File '{file_path}' already exists. "\
                "Use force mode to overwrite."
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
            cls._save_contacts_file(contact_file, force_mode, **kwargs)

        except (FileNotFoundError, IOError, json.JSONDecodeError) as e:
            raise cls.EncryptionError(e) from e

        else:
            logger.info("File encrypted")


class ContactsEdit(_BaseContactsClass):
    '''
    Edit contacts file

    '''

    class EditingError(ModuleBaseException):
        def __init__(self, *args, **kwargs):
            super().__init__(error_title="Contacts file editing error",
                             *args, **kwargs)

    @classmethod
    def add_key(cls,
                api_key_name: str,
                api_key_value: Optional[str] = None,
                file_key: Optional[bytes] = None,
                set_default: Optional[bool] = False,
                force_mode: Optional[bool] = False,
                autoconfirm: Optional[bool] = False,
                ) -> None:

        contacts_dict = cls._load_contacts_file()

        if api_key_name in cls._RESERVED_NAMES:
            raise cls.EditingError(cls.ReservedValueError)

        if not force_mode:

            if api_key_name in contacts_dict:
                error = "API-key with this name already exists, "\
                    "use force-mode to override or choose another name"
                raise cls.EditingError(error)

            elif api_key_value is None:
                error = "API-key is not provided, "\
                "use force mode to save key without value"
                raise cls.EditingError(error)

            Checkers.check_api_key(api_key_value=api_key_value)

        if api_key_value is None and not autoconfirm:

            while True:
                action = input("Save empty API-key? (y/N)")

                if not action or action.lower() == "n":
                    error = "Operation aborted by user"
                    raise cls.EditingError(error)

                elif action.lower() == "y":
                    break

        contacts_dict["bots"][api_key_name] = api_key_value

        if set_default:
            contacts_dict["default_bot_name"] = api_key_name

        cls._save_contacts_file(contacts_dict, force_mode = True)

        api_is_none = ", the key value is empty" if api_key_value is None else ""
        is_default = ", the key set as default" if set_default else ""
        logger.info(f"api-key '{api_key_name}' saved" + api_is_none + is_default)

    def del_key(api_key_name) -> None:
        pass

    def set_default() -> None:
        pass


class ContactsShow(_BaseContactsClass,
                   metaclass = _CallableClassMeta,
                   class_call_method = "_print_contacts"):

    @classmethod
    def _print_contacts(cls) -> None:

        contacts_dict = cls._load_contacts_file()

        pp = pprint.PrettyPrinter()
        pp.pprint(contacts_dict)

        # here will be logic to print contacts with filter, only one value, with custom formating etc.


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


class CreateDispatcher(_BaseContactsClass,
                       metaclass=_CallableClassMeta,
                       class_call_method="_dispatcher_factory"):

    '''
    read contacts file for chat id accoring gived names and return
    a Dispatcher object.

    main arguments:
    api_key_name: str - name of saved api-key, default is "default" -
    saved in contacts default chat_name


    recipients arguments:

    bulk_groups: string or itarable of strings
    with names of bulk groups as stored

    chat_names: same as bulk_groups, but more accurate
    (bulk_groups are stored as sets, chat_names as dictionary)

    manual_chats: integer or iterable of integers
    (dictonaries as {int: name})


    optional hidden arguments:

    api_key_value: str - if you dont save api_key to contacts file,
    you have to provide it now

    file_key: str - if use not default one.

    found_only: bool - dont raise an error,
    if some name of bulk_group or chat_name is not found
    '''

    class DispatcherConfiguratingError(ModuleBaseException):
        def __init__(self, *args, **kwargs):
            error_title = "An error occurred during creating configurations for despatcher"
            super().__init__(*args, **kwargs, error_title=error_title)

    @classmethod
    def _dispatcher_factory(cls,
                            api_key_name: str = "default",
                            chat_names: Union[str, Iterable[str]] = None,
                            bulk_groups: Union[str, Iterable[str]] = None,
                            manual_chats: Union[int, Iterable[int]] = None,
                            found_only: bool = False,
                            **kwargs
                            ) -> Dispatcher:

        deeper_kwargs = {key: kwargs[key] for key in ["file_key"]
                         if key in kwargs}

        contacts_dict = cls._load_contacts_file(**deeper_kwargs)

        if api_key_name == "default":
            api_key_name = contacts_dict.get("default_bot")
            logger.debug("Using default api-key")

            if api_key_name not in contacts_dict["bots"]:
                error_message = f"default value {api_key_name} "\
                    "is not presented in saved contacts list"
                raise cls.DefaultValueError(error_message=error_message)

        if api_key_name not in contacts_dict["bots"]:
            error_message = f"Api-key '{api_key_name}' not found in list of "\
                "saved bots' names."
            raise cls.DispatcherConfigurationError(error_message=error_message)

        api_key_value = contacts_dict["bots"][api_key_name]

        if kwargs.get("api_key_value"):

            if api_key_value:
                error_message = f"Another api-key saved to by name" \
                    f"'{api_key_name}' and cannot be replaced."
                raise cls.CreatingConfiurationsError(
                    error_message=error_message)

            else:
                api_key_value = kwargs["api_key_value"]

        if all(arg is None for arg in (chat_names, bulk_groups, manual_chats)):

            default_chat = contacts_dict["default_chat"]

            if not default_chat:
                error_message = "No recipients specified. "\
                    "Default chat is not specified"
                raise cls.DispatcherConfiguratingError(
                    error_message=error_message)

            elif default_chat not in contacts_dict["chat_names"]:
                error_message = f"Default value {default_chat} "\
                    "is not presented in saved contacts list"
                raise cls.DefaultValueError(
                    error_message=error_message)

            else:
                chat_names = default_chat

        recipients = dict()
        not_found = []

        if manual_chats:

            logger.debug("Adding manually provided items.")

            if isinstance(manual_chats, int):
                manual_chats = {manual_chats}

            elif isinstance(manual_chats, dict):
                recipients.update(manual_chats)

            else:
                manual_chats = dict.fromkeys(manual_chats, "manually provided")
                recipients.update(manual_chats)

        if bulk_groups:

            logger.info("Adding bulk groups.")

            searching_groups = {bulk_groups} if isinstance(bulk_groups, str) \
                else set(bulk_groups)

            existing_groups = set(contacts_dict["bulk_groups"])

            found_groups = searching_groups.intersection(existing_groups)
            not_found_groups = searching_groups.difference(existing_groups)

            if found_groups:

                for group in found_groups:

                    adding_group = dict.fromkeys(
                        contacts_dict["bulk_groups"][group],
                        f"bulk group '{group}'")

                    overwriting_recipients = {
                        key: f"{recipients[key]}, bulk group '{group}'"
                        for key in adding_group.keys() & recipients.keys()
                    }

                    recipients.update(adding_group)
                    recipients.update(overwriting_recipients)

            if not_found_groups:
                not_found.append("bulk_groups: " + ", ".join(not_found_groups))

        if chat_names:

            logger.info("Adding chat names.")

            searching_chats = {chat_names} if isinstance(chat_names, str) \
                else set(chat_names)
            existing_chats = contacts_dict["chat_names"]

            found_chats = searching_chats.intersection(existing_chats.keys())
            not_found_chats = searching_chats.difference(existing_chats.keys())

            if found_chats:

                adding_chats = {existing_chats[name]: f"chat name '{name}'"
                                for name in found_chats}

                overwriting_recipients = {key: f"{recipients[key]}, chat name '{name}'"
                                          for name in adding_chats.keys() & recipients.keys()}

                recipients.update(adding_chats)
                recipients.update(overwriting_recipients)

            if not_found_chats:
                not_found.append("chat_names: " + ", ".join(not_found_chats))

        if not_found:

            error_message = ("These names were not found:\n"
                             "\n".join(not_found))

            if found_only:
                raise cls.DispatcherConfigurationError(
                    error_message=error_message)

            else:
                logger.info(error_message)
                print(error_message)

        if not recipients:
            error_message = "Recipients list is leer"
            raise cls.DispatcherConfigurationError(error_message=error_message)

        return Dispatcher(api_key_value=api_key_value,
                          api_key_name=api_key_name,
                          recipients=recipients,
                          **kwargs)
