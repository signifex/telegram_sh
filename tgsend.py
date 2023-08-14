#!/usr/bin/env python3

'''
About this script:
I wanted to create a simple script that sends messages to telegram from bash.
But writing complex logic on the bash is such a thing.
Therefore, I wrote in Python, and the first version generally used bare arguments instead of an argument's parser lib.
Then I added sending docks as the first upgrade. Then I decided to add a good implementation to other scripts.
But with all this, the script still can work on the standard library,
and only to send documents the requests module is needed.

NOTE:
ContactsFile is not really encrypted, it is simple byte exchange, to prevent direct reading.

This is the third version of the script, for next one:

1) I need to find out, that about groups of arguments in argparse module in  python 3.11/3.12

2) mb think about real encryption of contacts file?
   but I dont know, how to realise it using built-in libs only.

3) ADD SENDING OF ALREADY OPEN DOCUMENT

4) aiohttp supporting
'''


# -------------------------------------------------------- imports --------------------------------------------------------- #

import os
import sys
import argparse
import json
import traceback
import datetime
import hashlib
import logging
import asyncio
import urllib.request
import urllib.parse

from typing import List, Set, Dict, Tuple, NamedTuple, Literal, Union, Iterable, BinaryIO, Optional, NoReturn

try:
    import requests
    REQUESTS = True
except ImportError:
    REQUESTS = False

try:
    import aiohttp
    AIOHTTP = True
except ImportError:
    AIOHTTP = False


# ------------------------------------------------------- constants -------------------------------------------------------- #

EXIT_STATUS = Literal[0, 1]

FILE_KEY = 0x11
'''
Feel free to change the key, anyway, it is only 256 possible values,
and provide only weak protection from direct file reading.
If you dont want to save api-keys, you can always provide it manually, and not storing value in ContactsFile.
Only api_key_name is required to manage contacts associated with the bot
'''

# ----------------------------------------------------- set up logger ------------------------------------------------------ #

def logging_level(verbose=False):

    if verbose:
        logging.basicConfig(level=logging.DEBUG)

    else:
        logging.basicConfig(level=logging.WARNING)


# -------------------------------------------------------- classes --------------------------------------------------------- #

class Colorize:

    '''
    Donno how it works in other shells, so be careful about it. I dont dive a fuck.
    Actually it is a shorted version of my another module, but I want to make this script
    as independent, as possible
    '''

    RESET_COLOR = "\033[0m"

    COLORS = {
    "black": "\033[30m",
    "red": "\033[31m",
    "green": "\033[32m",
    "yellow": "\033[33m",
    "blue": "\033[34m",
    "magenta": "\033[35m",
    "cyan": "\033[36m",
    }

    STYLES = {
        "bold": "\033[1m",
    }

    END_STYLES = {
        "bold": "\033[22m",
    }

    def __init__(self,
                 text: str,
                 color: Optional[str] = None,
                 bold: Optional[bool] = False,
                 ) -> NoReturn:

        self._color = color
        self._text = text
        self._bold = bold

    def __str__(self) -> str:

        style_code = []
        style_end = []

        if self._bold:
            style_code.append(self.STYLES["bold"])
            style_end.append(self.END_STYLES["bold"])

        if self._color:
            style_code.append(self.COLORS.get(self._color, ""))
            style_end.append(self.RESET_COLOR)

        return ''.join(style_code) + self._text + ''.join(reversed(style_end))


class ModuleBaseException(Exception):

    """
    ModuleBaseException is the foundational exception class for custom exceptions in this module.

    It's designed to capture and store detailed information about exceptions,
    making it easier to handle, log, and report errors. Child exceptions derived
    from this class can provide more specific error contexts or messages.

    Attributes:
        original_exception: The original exception that triggered the custom exception.
        error_name: A string representing the context or part of the module where the error occurred.
        error_message: A general error message that provides context about the error.
        logging_string: A formatted string suitable for logging that combines all the details.

    Usage:
        This class is intended to be subclassed for specific exception types and
        should not be raised directly. When creating a child exception,
        provide the original exception and an optional custom message to the
        initializer. When handling the exception, you can access its attributes
        for custom error reporting or logging.

        Example:
            ...
            class CustomError(ModuleBaseException):
                super().__init__(original_exception, "error name")
            ...

            try:
                1/0
            except ZeroDivisionError as e:
                raise CustomError(e) from e
            ...

            try:
               (call function with last try-catch block)
            except ModuleBaseException as e:
                print(e)
                print(e.log)
                logger.error(e.traceback)
            ...

    Note:
        Catching `ModuleBaseException` in error handlers will also catch all
        its child exceptions.
    """

    def __init__(self, original_exception: Exception, error_name: str):
        super().__init__(str(original_exception))

        # Store the attributes
        self.original_exception = original_exception
        self.name = error_name
        self.message = str(original_exception)
        self.traceback = ''.join(traceback.format_exception(type(original_exception), original_exception, original_exception.__traceback__))
        self.log = "\n".join(("\n" + datetime.datetime.now().strftime("%Y.%m.%d %H:%M:%S"), self.__str__(), self.traceback))

    def __str__(self):
        return f"{self.name}: {self.message}"


class Utilities:

    '''
    A bunch of secondary functions.
    Checkers to prevent errors.
    Timestamp to get unique key for dictionaries.
    '''

    class CheckFailed(ModuleBaseException):
        def __init__(self, original_exception):
            super().__init__(original_exception, "Check failed")


    def check_api_key(api_key: str) -> NoReturn:
        url = f"https://api.telegram.org/bot{api_key}/getMe"

        try:
            response = urllib.request.urlopen(base_url)
            data = json.load(response)

            if not data["ok"]:
                raise ValueError("API-key's check failed")

            logger.info("API-key's check passed")

        except (urllib.error.URLError, ValueError) as e:
            raise CheckFailed(e) from e


    def check_files(packets: List[str]) -> NoReturn:

        min_size = 1
        max_size = 50 * 1024 * 1024

        fucked_up_packages = {}

        for packet in packets:

            if not os.path.exists(packet):
                fucked_up_packages[packet] = "File not found"

            elif not os.path.isfile(packet):
                fucked_up_packages[packet] = "Not a file"

            elif min_size > os.path.getsize(packet) > max_size:
                fucked_up_packages[packet] = "File must be not empty and less than 50 MB"

        if fucked_up_packages:
            error = "\n" + "\n".join([f"{key}: {value}" for key, value in fucked_up_packages.items()])
            raise CheckFailed(ValueError(error))


    def check_audiofiles(packets: List[str]) -> NoReturn:

        min_size = 1
        max_size = 50 * 1024 * 1024

        allowed_formats = ["mp3", "ogg", "wav"]

        fucked_up_packages = {}

        for packet in packets:

            if not os.path.exists(packet):
                fucked_up_packages[packet] = "File not found"

            elif not os.path.isfile(packet):
                fucked_up_packages[packet] = "Not a file"

            elif min_size > os.path.getsize(packet) > max_size:
                fucked_up_packages[packet] = "File must be not empty and less than 50 MB"

            elif os.path.splitext(packet)[1] not in allowed_formats:
                fucked_up_packages[packet] = f"File must be: {allowed_formats}"

        if fucked_up_packages:
            error = "\n" + "\n".join([f"{key}: {value}" for key, value in fucked_up_packages.items()])
            raise CheckFailed(ValueError(error))

    def get_timestamp() -> str:
        return datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S_%f")


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

    api_key = property(_get_api_key)

    recipients = property(_get_recipients)

    def __init__(self,
                 api_key: str,
                 recipients: Iterable[int],
                 api_key_name: Optional[str] = None):

        self._api_key = api_key
        self.api_key_name = api_key_name
        self._recipients = recipients.copy() if isinstance(recipients, dict) else dict.fromkeys(recipients)

        logger.info(f"Data for sending messages is formed, amount of recipients: {len(self._recipients)}")

        return self

    def _get_api_key(self) -> Tuple[str, str]:
        return self._api_key, self.api_key_name


    def _get_recipients(self) -> Dict:
        return self._recipients


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

        logger.info("Using manual provided api-key")
        return self


    def add_recipients(self,
                       recipients: Iterable[str],
                       overwrite_names: bool = False):

        if isinstance(recipients, dict) and overwrite_names:
            self._recipients.update(recipients)

        else:
            for recipient in recipients:
                self._recipients.setdefault(recipients)

        logger.info("Recipients list updated")
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


    class CreatingError(ModuleBaseException):
        def __init__(self, original_exception):
            super().__init__(original_exception, "File creating error")


    class FileCorruptedError(ModuleBaseException):
        def __init__(self, original_exception):
            super().__init__(original_exception, "File corrupted")


    class SavingError(ModuleBaseException):
        def __init__(self, original_exception):
            super().__init__(original_exception, "File not saved")


    class LoadingError(ModuleBaseException):
        def __init__(self, original_exception):
            super().__init__(original_exception, "File not loaded")


    class ReservedValueError(Exception):
        def __str__(self):
            error = "This values are reserved: " + ", ".join(ContactsFile.RESERVED_NAMES)
            return error


    class Copy:

        class DecryptionError(ModuleBaseException):
            def __init__(self, original_exception):
                super().__init__(original_exception, "Decryption error")

        class EncryptionError(ModuleBaseException):
            def __init__(self, original_exception):
                super().__init__(original_exception, "Encryption error")

        def decrypt(file_path: Optional[str] = "tgsend.contacts.decrypted",
                    file_key: Optional[bytes] = FILE_KEY,
                    force_mode: Optional[bool] = False,
                    )-> NoReturn:

            contact_file = ContactsFile._load(file_key = file_key)

            if not force_mode and os.path.exists(file_path):
                raise DecryptionError(FileExistsError(f"File '{file_path}' already exists. Use force mode to overwrite."))

            try:
                with open(file_path, "w") as copy:
                    json.dump(contact_file, copy)
                logger.info("File decrypted")

            except (FileNotFoundError, IOError) as e:
                raise DecryptionError(e) from e


        def encrypt(file_path: str,
                    file_key: Optional[bytes] = FILE_KEY
                    ) -> NoReturn:

            try:
                with open(file_path, "r") as copy:
                    contact_file = json.load(copy)
                ContactsFile._save(contact_file, file_key=file_key)
                logger.info("File encrypted")

            except (FileNotFoundError, IOError, json.JSONDecodeError) as e:
                raise EncryptionError(e) from e


    class Edit:

        '''
        Edit contacts file

        '''

        class EditingError(ModuleBaseException):
            def __init__(self, original_exception):
                super().__init__(original_exception, "File editing error")


        def add_api_key(api_key_name: str,
                        api_key: Optional[str] = None,
                        file_key: Optional[bytes] = FILE_KEY,
                        set_default: Optional[bool] = False,
                        force_mode: Optional[bool] = False,
                        autoconfirm: Optional[bool] = False,
                        ) -> NoReturn:

            contacts_dict = ContactsFile._load()

            if api_key_name in ContactsFile.RESERVED_NAMES:
                raise EditingError(ContactsFile.ReservedValueError)

            if not force_mode:

                if api_key_name in contacts_dict:
                    error = ValueError("API-key with this name already exists, use force-mode to overwrite")
                    raise EditingError(error)

                elif api_key is None:
                    error = ValueError("API-key is not provided, use force mode to save key without value")
                    raise EditingError(error)

                Utilities.check_api_key(api_key = api_key)

            if api_key is None and not autoconfirm:

                while True:
                    action = input("Save empty API-key? (y/N)")

                    if not action or action.lower() == "n":
                        error = KeyboardInterrupt("Operation aborted by user")
                        raise EditingError(error)

                    elif action.lower() == "y":
                        break

            contacts_dict[api_key_name] = ContactsFile._key_structure
            contacts_dict[api_key_name]["api_key"] = api_key

            if set_default:
                contacts_dict["default"] = api_key_name

            cls._save(contacts_dict)

            api_is_none = ", the key value is empty" if api_key is None else ""
            is_default = ", set as default" if set_default else ""
            logger.info(f"api-key key {api_key_name} saved" + api_is_none + is_default)


    @classmethod
    def create(cls,
               api_key_name: str,
               api_key: Optional[str] = None,
               file_key: Optional[bytes] = FILE_KEY,
               set_default: Optional[bool] = True,
               force_mode: Optional[bool] = False,
               autoconfirm: Optional[bool] = False
               ) -> NoReturn:

        if api_key_name in cls.RESERVED_NAMES:
            raise cls.ReservedValueError

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

        except (cls.ReservedValueError, FileExistsError) as e:
            raise cls.CreatingError(e) from e

        except KeyboardInterrupt:
            raise cls.CreatingError(KeyboardInterrupt("Operation aborted by user"))


    @classmethod
    def _load(cls, file_key = FILE_KEY) -> dict:

        try:

            with open(cls._path, mode = "rb") as file:
                binary_data = file.read()

            encrypted_data = binary_data[:-64]

            stored_hash = binary_data[-64:]

            new_hash = hashlib.sha256(encrypted_data).hexdigest().encode()

            if new_hash != stored_hash:
                error = f"file {cls._name} corrupted"
                raise FileCorruptedError(error)

            decrypted_data = bytearray(byte ^ key for byte in encrypted_data)

            contacts_dict = json.loads(decrypted_data.decode())

            return contacts_dict

        except cls.FileCorruptedError as e:
            raise e

        except FileNotFoundError:
            error = f"file not found: {cls._path}"
            raise FileNotFoundError(error)

        except json.JSONDecodeError:
            error = f"file not decoded into dictionary: {cls._path}"
            raise json.JSONDecodeError(error)

        except Exception as e:
            error = f"error during reading '{cls._path}'" + str(e)
            raise Exception(error)


    @classmethod
    def _save(cls, new_file, key: bytes = FILE_KEY) -> NoReturn:

        json_data = json.dumps(new_file)

        encrypted_data = bytearray(byte ^ key for byte in json_data.encode())

        new_hash = hashlib.sha256(encrypted_data).hexdigest().encode()

        export_data = encrypted_data + new_hash

        with open(cls._path, "wb") as file:
            file.write(export_data)


    @classmethod
    def show_contacts(cls, api_key_name:str) -> NoReturn:

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
                               searching_chat_names: Union[str, Iterable[str]] = None,
                               searching_bulk_groups: Union[str, Iterable[str]] = None,
                               manual_id: Union[int, Iterable[int]] = None,
                               ) -> SendingConfigs:

        '''
        read contacts file for chat id accoring gived names and return a SendingCofigs object.


        '''
        contacts_dict = cls._load()

        if api_key_name not in contacts_dict.keys():
            error = "name of api-key not found in  contacts file"
            raise ValueError(error)

        elif api_key is not None:
            saved_api_key = contacts_dict[api_key_name][api_key]
            if saved_api_key != "":
                error = f"another api-key saved to by name '{api_key_name}'"
                raise ValueError(error)

        elif all(arg is None for arg in (searching_chat_names, searching_bulk_groups, manual_id)):
            error = "No recipients specified"
            raise ValueError (error)

        recipients = dict()
        not_found = dict()

        if searching_bulk_groups is not None:

            if isinstance(searching_bulk_groups, str):
                searching_bulk_groups = {searching_bulk_groups}
            else:
                searching_bulk_groups = set(searching_bulk_groups)

            bulk_groups = contacts_dict[api_key_name]["bulk_groups"]
            not_found["bulk_groups"] = {group for group in searching_bulk_groups if group not in bulk_groups}
            found_groups = searching_bulk_groups - not_found["bulk_groups"]
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

        if searching_chat_names is not None:

            if isinstance(searching_chat_names, str):
                searching_chat_names = {searching_chat_names}

            contacts = contacts_dict[api_key_name]["contacts"]

            found_contacts = {value: key for key, value in contacts.items() if key in searching_chat_names}

            not_found["contacts"] = {name for name in searching_chat_names if name not in contacts}

            for key, value in found_contacts.items():
                recipients.setdefault(key, value)


        if not_found:
            print("These names not found:")
            for key, value in not_found.items():
                print(key, ": ", *value)

        if not contacts:
            print("Recipients list is leer")

        return SendingConfigs(api_key = api_key, api_key_name = api_key_name, recipients = recipients)




class GetContacts(ContactsFile):

    class Message(NamedTuple):
        chat_id: int
        username: str
        first_name: str
        text: str

        
    @classmethod
    def from_updates(cls,
                     api_key_name: str,
                     api_key: str = None,
                     filter_username: str = None,
                     filter_text: str = None) -> NoReturn:

        contacts_dict = super()._load()

        if api_key_name not in contacts_dict:
            error = f"api-key '{api_key_name}' is not exists in contacts file"
            raise ValueError(error)

        if api_key is not None:
            api_key = contacts_dict[api_key_name]["api_key"]
            logger.info("api key taken from contacs file")

        Utilities.check_api_key(api_key)


    def _get_updates(api_key: str) -> List:

        url = f'https://api.telegram.org/bot{api_key}/getUpdates'

        logger.info("Getting updates from Telagram server")

        try:

            with urllib.request.urlopen(url) as response_raw:
                response = json.loads(response_raw.read())

            if not response.get("ok"):
                error = "Wrong API-call"
                raise ValueError(error)

            elif response["result"] == []:
                error = "no updates, send some message to bot, and try again"
                raise ValueError(error)

            logger.info("returing data from Telegram server")
            return response["result"]

        except Exception as e:
          error = "error retrieving data from Telegram server: " + e.args[0]
          raise Exception(error)


    def _format_messages(messages: list[Message]) -> list[Message]:

        '''
        get "result" friom Telagram, extact values and form Message class from each message
        '''
        logger.info("messages formating starts")

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

        formated_messages = formated_messages_dict.values()

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




class Dispatcher:

    '''
    Dispatcher takes:

    for 'send' function:
    NOTE: messages can be send also without requests library

    messages - list of messages, will be send for each recipient one-by-one
    ["message1", "message2"]

    documents - list of files' pathes, will be skipped, if module requests not imported
    default mode for each file
    ["path_to_file1", "path_to_file2"]

    audiofiles - list of audiofiles' paths, same as documents
    (audiofiles can be sent as a regular files(document), in that case user will not be able to play audiofiles in telegram)

    probably i will add some new feachers to send photos, stickers etc,
    but now I'm using this module to send files and messages from bash,
    or critical-level erros from other scripts

    Send function returns:
    dictionary of successfully sent messages(documents, audiofiles, etc)
    and a dictionary of unsuccessful ones
    and control sum of all packeges. that were taken.

    both dictionaries have structure like:
    {timestamp: description}
    '''

    FILE_TYPES = Literal["files", "audiofiles"]

    class SendingStatus(NamedTuple):
        success: Dict[str, str]
        fail: Dict[str, str]

    def __init__(self, configs: SendingConfigs) -> NoReturn:

        self._api_key: str = configs.api_key
        self.api_key_name: str = configs.api_key_name
        self._recipients: Dict[int, str] = configs.recipients.copy()

        self._sending_success = {}
        self._sending_errors = {}

        self._invalid_packets = {}

        Utilities.check_api_key(self.api_key)

    def _get_api_key(self):
        return self._api_key, self._api_key_name
    api_key = property(_get_api_key)

    def _get_recipients(self):
        return self._recipients
    recipients = property(_get_recipients)

    async def _message_handler(self, message) -> NoReturn:

        tasks = [self._message_dispatcher(messages, recipient_id, recipient_name) for recipient_id, recipient_name in self._recipients.values()]

        await asyncio.gather(*tasks)


    async def _message_dispatcher(self, messages: str, recipient_id: int, recipient_name: str) -> NoReturn:

        url = f"https://api.telegram.org/bot{self.api_key}/sendMessage"

        params = {"chat_id": recipient_id, "text": message}

        data = urllib.parse.urlencode(params).encode("utf-8")

        with await urllib.request.urlopen(url, data) as response:
            response_data = response.read().decode("utf-8")
            response_json = json.loads(response_data)

        key = Utilities.get_timestamp()

        if response_json.get("ok"):
            self._sending_success[key] = f"recipient: {recipient_id}/{recipient_name}"

        else:
            error_description = response_json.get("description", "Unknown error")
            description = f"recipient: {recipient_id}/{recipient_name}\n{error_description}"
            self._sending_errors[key] = description


    async def _files_handler(self, packets: List[str], packets_type: FILE_TYPES, caption: Optional[str] = None) -> NoReturn:


        if packet_type == "audiofiles":
            url = f"https://api.telegram.org/bot{self.api_key}/sendAudio"

        else:
            url = f"https://api.telegram.org/bot{self.api_key}/sendDocument"

        open_files = [("document", open(packet, "rb")) for packet in packets]

        tasks = [self._files_dispatcher(url, open_files, recipient_id, recipient_name, caption) for recipient_id, recipient_name in self.recipients.items()]

        await asyncio.gather(*tasks)


    async def _files_dispatcher(self,
                                url: str,
                                open_files: List[BinaryIO],
                                recipient_id: int,
                                recipient_name: str,
                                caption: Optional[str]
                                ) -> NoReturn:

        data = {"chat_id": recipient_id}

        if caption:
            data["caption"] = caption

        response = await requests.post(url, data = data, files = open_files)

        key = Utilities.get_timestamp()

        if response.status_code == 200:
           self._sending_success[key] =  f"recipient: {recipient_id}/{recipient_name}"

        else:
           description = f"recipient: {recipient_id}/{recipient_name}\n" + str(json.loads(response.content)["description"])
           self._sending_errors[key] = description

    def send_message(self, message: str) -> SendingStatus:

        self._sending_success.clear()
        self._sending_errors.clear()

        if len(package) > 4096:
            raise ValueError("message is too long: max 4096 symbols per one message")

        asyncio.run(self._message_handler(message))

        return SendingStatus(successful = self._sending_success, failed = self._sending_errors, checksum = len(self.recipients))


    def send_files(self, packets: List[str]) -> SendingStatus:

        if not REQUESTS:
            raise ImportError("Files can't be send without 'requests' library")

        self._sending_success.clear()
        self._sending_errors.clear()

        Utilities.check_files(packets = packets)

        checksum = len(self.recipients) * len(packet)

        asyncio.run(self._file_handler(packets = packets, p_type = "files"))

        return SendingStatus(success = self._sending_success, fail = self._sending_errors, checksum = checksum)

    def send_audiofiles(self, packets: List[str]) -> SendingStatus:

        if not REQUESTS:
            raise ImportError("Files can't be send without 'requests' library")

        Utilities.check_audiofiles(packets = packets)

        self._sending_success.clear()
        self._sending_errors.clear()

        checksum = len(self.recipients) * len(packets)

        asyncio.run(self._file_handler(packets = packets, p_type = "audiofiles"))

        return SendingStatus(success = self._sending_success, fail = self._sending_errors, checksum = checksum)




class Handler:

    '''
    Main class of this script with a couple of function:

    handler - wrapper for dispatcher, that also extracts values from contacts file,
    deals with errors and calls dispatcher with extracted values.

    Basicly, handler is good for for one-time calling of the script, from terminal or another script.

    But to avoid multiple opening of contacts file, you can use Dispatcher with values,
    extracted from contacts file using ContactsFile.get_values

    Also it will be better for logging, couse Dispatcher.send returns dictionaries of
    sending good and bad messages or/and files (and control sum of packages for sure).
   '''

    @classmethod
    def dispatcher_wrapper(cls,
                           api_key: str = None,
                           api_key_name: str = None,
                           chat_id: int = None,
                           chat_name: str = None,
                           print_success: bool = True,
                           messages: list[str] = [],
                           documents: list[str] = [],
                           audiofiles: list[str] = []
                           ) -> EXIT_STATUS:

        try:

            # this shit will raise an error when will provided no arguments or both
            if (api_key and api_key_name) or (not api_key and not api_key_name):
                error = "saved API-key name (using -A flag for non-defualt values) OR manually provided API-key (using -M flag) required"
                raise ValueError(error)

            elif (chat_id and chat_name) or (not chat_id and not chat_name):
                error = "chat id name (from contacts file, using -t flag for non-default values) OR manually provided (using -T flag) required"
                raise ValueError(error)

            elif not any((messages, documents, audiofiles)):
                error = "nothing to send"
                raise ValueError(error)

            # get values according providen names
            extracted_values = ContactsFile.get_values(api_key_name = api_key_name, chat_name = chat_name)

            api_key = extracted_values.get("api_key", api_key)
            chat_id = extracted_values.get("chat_id", chat_id)

            one_time_dispatcher = Dispatcher(api_key = api_key, chat_id = chat_id)

            status_dictionaries = one_time_dispatcher.send(messages = messages,
                                                           documents = documents,
                                                           audiofiles = audiofiles)

            exit_status = cls._status_printer(status_dictionaries,
                                              print_success = print_success)

        except (Exception, BaseException) as e:

            exit_status = 2
            if isinstance(e, (SystemExit, KeyboardInterrupt)):
                raise

            else:
               error = Colorize(text = e.args[0], color = "red")
               print(error)

               # traceback.print_exc()

        finally:
            return exit_status


    def _status_printer(status: Dispatcher.SendingStatus, print_success = True) -> EXIT_STATUS:

        exit_status = 0

        amount = len(status.sending_success) + len(status.sending_errors)

        if amount != status.checksum:
            message = Colorize(text = f"amount of packages({amount}) is not equal to checksum({status.checksum})", color = "magenta", bold = True)
            print(message)
            print("success:\n", *status.sending_success.items(), sep = "\n"),
            print("failure:\n", *status.sending_errors.itmes(), sep = "\n")
            exit_status = 2

        elif len(status.sending_success) == status.checksum:
            if print_success:
                message = Colorize(text = "all packages successfully delivered", color = "green")
                print(message)
            exit_status = 0

        elif len(status.sending_errors) == status.checksum:
            message = Colorize(text = "errors by sending all packages:", color = "red")
            print(message)
            print(*status.sending_errors.values(), sep = "\n")
            exit_status = 2

        else:
            if print_success:
                message = Colorize(text = "some packages successfully delivered:", color = "green")
                print(message)
                print(*status.sending_success.values(), sep = "\n")

            message = Colorize(text = "some packages are not delivered:", color = "red")
            print(message)
            print(*status.sending_errors.values(), sep = "\n")
            exit_status = 1

        return exit_status




# ------------------------------------------------------- main part -------------------------------------------------------- #


def main() -> EXIT_STATUS:

    exit_status = 0

    # setup parser and subparser
    parser = argparse.ArgumentParser(description = "Send messages or/and documents from shell to Telegram bot",
                                     epilog = "https://github.com/signifex")

    subparsers = parser.add_subparsers(title = "commands",
                                       description = "valid commands",
                                       dest = "command",
                                       help = "description")


    # main parser for sending messages and documents
    message_handler_parser = subparsers.add_parser("send", help = "send message or file to chat")

    api_key = message_handler_parser.add_mutually_exclusive_group(required = False)

    api_key.add_argument("-k", "--api_key",
                         metavar = "<name of saved API-key>",
                         dest = "api_key_name",
                         help = "saved bot's api key, by default will be readed from contacts file")

    api_key.add_argument("-K", "--manual_api_key",
                         metavar = "<API-key>",
                         dest = "api_key",
                         help = "manual provided API-key")

    recipient = message_handler_parser.add_mutually_exclusive_group(required = False)

    recipient.add_argument("-c", "--to_saved_chat",
                           metavar = "<saved chat name>",
                           dest = "chat_name",
                           type = str,
                           help = "name from contacts list to send message")


    recipient.add_argument("-C", "--to_manual_chat",
                           metavar = "<chat id>",
                           dest = "chat_id",
                           type = int,
                           help = "manual provided chat_id to send message")

    packages = message_handler_parser.add_argument_group()

    packages.add_argument("-m", "--message",
                          metavar = "message",
                          dest = "messages",
                          nargs = "+",
                          action = "extend",
                          default = [],
                          help = "send message(s) to chat")


    packages.add_argument("-d", "--document",
                          metavar = "file",
                          dest = "documents",
                          nargs = "+",
                          action = "extend",
                          default = [],
                          help = "send file(s) to chat")


    packages.add_argument("-a", "--audio",
                          metavar = "audiofile",
                          dest = "audiofiles",
                          nargs = "+",
                          action = "extend",
                          default = [],
                          help = "send audiofile(s) to chat")


    # parser for creating contacts file, API key is optional
    creation_file_parser = subparsers.add_parser("create", help = "create contacts file")

    creation_file_parser.add_argument("-k", "--api_key",
                                      metavar = "API-key",
                                      dest = "creation_api_key",
                                      type = str,
                                      help = "create contacts file for bot with provided api-key")

    # parser to only show contacts list

    list_contacts_parser = subparsers.add_parser("list", help = "show contacts list and exit")

    # parser for contacts file

    contacts_edit_parser = subparsers.add_parser("contacts", help = "edit contacts file")

    editor = contacts_edit_parser.add_mutually_exclusive_group(required = True)

    editor.add_argument("-a", "--add",
                        metavar = ("contact", "chat"),
                        dest = "editor_add",
                        nargs = 2,
                        help = "add contact with followed chat-number to contacts")

    editor.add_argument("--remove",
                        metavar = "<chat name>",
                        dest = "editor_remove",
                        help = "remove saved contacts")

    # parser to get updates - easy way to get own chat number

    get_id_parser = subparsers.add_parser("getid", help = "get updates from bot and return messages with chat id")

    get_id_parser.add_argument("-A", "--api_key",
                               metavar = "API-key",
                               dest = "get_id_api_key",
                             #  default = ,
                               help = "use this API to get chat, or, by default will be taken from contacts file")


    searching_element = get_id_parser.add_mutually_exclusive_group(required = False)

    searching_element.add_argument("-u", "--username",
                                   metavar = "<username>",
                                   dest = "get_id_by_username",
                                   help = "parse last messages to get chat id by provided username")

    searching_element.add_argument("-t", "--text",
                                   metavar = "<text>",
                                   dest = "get_id_by_text",
                                   help = "parse last messages to get chat id by proveded text")


    # read arguments

    args = parser.parse_args()


    # call functions by argument command
    print(args)

    if args.command == "create":
        ContactsFile.create(api_key = args.creation_api_key)

    elif args.command == "getid":
        print(Colorize(text = "function not ready", color = yellow, bold = True))
        # get_id(api_key = args.get_id_api_key, searching_username = args.get_id_by_username, searching_text = args.get_id_by_text)

    elif args.command == "list":
        ContactsFile.print_values()

    elif args.command == "contacts":
        contacts_editor(chat_add = args.editor_add, chat_remove = args.editor_remove)

    elif args.command == "send":

        '''
        IMPORTANT NOTE:
        I checked documentation for argparse module, and have to mark 2 points:
        1) If i understood correctly, add_mutally_exclusive_group will be removed in python 3.11 (my current version - 3.10)
        So for next version of this module I have to found some other solution
        2) add_mutually_exclusive_group not support deleting or switching to None argument with default value, even if another argument for this group
        is provided by user. That creates a bug: I expect one or another key, but both keys with no-None values are provided.
        (raw api-key OR name of saved api-key, and the same for chat, in case of this script)

        Therefore, I use new variables based on args, and call Message.handler with not directly provided keys from argument parser, as I wanted first.
        BULLSHIT

        '''

        s_api_key = args.api_key
        s_api_key_name = args.api_key_name

        if not s_api_key and not s_api_key_name:
            s_api_key_name = "default"

        s_chat_id = args.chat_id
        s_chat_name = args.chat_name

        if not s_chat_id and not s_chat_name:
            s_chat_name = "default"

        # END OF BULLSHIT

        exit_status = Handler.dispatcher_wrapper(api_key = s_api_key,
                                                 api_key_name = s_api_key_name,
                                                 chat_id = s_chat_id,
                                                 chat_name = s_chat_name,
                                                 messages = args.messages,
                                                 documents = args.documents,
                                                 audiofiles = args.audiofiles)

    else:
        print(Colorize(color = "yellow", text = 'No command specified. Use --help for more information.'))

    return exit_status


# -------------------------------------------------- lets start this shit -------------------------------------------------- #

if __name__ == "__main__":
    exit_status = main()
    sys.exit(exit_status)

