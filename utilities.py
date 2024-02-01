import traceback
import datetime
import mimetypes
import urllib.request
import json

from io import BytesIO
from typing import Dict, Union, List, Tuple, BinaryIO, Optional, Iterable, NoReturn, NamedTuple

from . import logger

class _ModuleBaseException(Exception):

    """
    Base exception class to provide a consistent format for custom exceptions.
    This class is designed to be subclassed and should not be raised directly.

    _ModuleBaseException is the foundational exception class for custom exceptions in this module.

    It's designed to capture and store detailed information about exceptions,
    making it easier to handle, log, and report errors. Child exceptions derived
    from this class can provide more specific error contexts or messages.

    Attributes:
        original_exception (Exception): The original exception that triggered the custom exception.
                                        If no original exception is provided, it defaults to the custom exception itself.
        name (str): Name of the exception, typically the class name. Customizable.
        message (str): Detailed message of the error (or default error's message, will overwrite error's default message!)
        traceback (str): Stack trace of the error.
        log (str): Log message that combines the timestamp, error name, message, and traceback.

   Usage:
        This class is intended to be subclassed for specific exception types and
        should not be raised directly. When creating a child exception,
        provide the original exception and an optional custom message to the
        initializer. When handling the exception, you can access its attributes
        for custom error reporting or logging.

        Example:
            ...
            class CustomError(_ModuleBaseException):
                def __init__(*args)
                    super().__init__(args, error_title = "more functional name")
            ...

            try:
                1/0
            except ZeroDivisionError as e:
                raise CustomError(e)
            ...

            try:
               (call function with last try-catch block)
            except _ModuleBaseException as e:
                print(e)
                print(e.log)
                logger.error(e.traceback)
            ...

    Note:
        Catching `_ModuleBaseException` in error handlers will also catch all
        its child exceptions.
    """

    def __init__(self,
                 original_exception: Optional[Exception] = None,
                 error_title: Optional[str] = None,
                 error_message: Optional[str] = None):

        if self.__class__ == _ModuleBaseException:
            raise NotImplementedError("_ModuleBaseException should not be raised directly. Use a child class instead.")

        self.original_exception = original_exception if original_exception else self

        self.title = error_title if error_title else self.__class__.__name__

        self.message = str(self.original_exception) if original_exception else error_message

        if isinstance(original_exception, Exception):
            self.traceback = traceback.format_exception(type(original_exception), original_exception, original_exception.__traceback__)
        else:
            self.traceback = traceback.format_stack()[:-2]

        self.log = "\n".join(("\n" + _TimeStamp.log(), self.__str__(), ''.join(self.traceback)))

        logger.error(self.log)

        super().__init__(self.message)

    def __str__(self):
        return f"{self.title}:{self.message}"


class _CallableClassMeta(type):

    """
    Metaclass to make class callable at the class level.
    It checks that class_call_method is present in the class
    and calls it when the class is called.
    """

    def __new__(metacls, name, bases, namespace, class_call_method):

        if class_call_method not in namespace:
            raise AttributeError(f"'{class_call_method}' method not found in {name}")

        cls = super().__new__(metacls, name, bases, namespace)

        cls.__class_call_method = namespace[class_call_method]

        if not callable(cls.__class_call_method):
            raise AttributeError(f"'{class_call_method}' must be a callable method in {name}")

        return cls

    def __call__(cls, *args, **kwargs):
        return cls.__class_call_method(*args, **kwargs)


class Checkers:

    class FileCheckError(_ModuleBaseException):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs, error_name = "Check failed")

    class ApiKeyCheckError(_ModuleBaseException):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs, error_name = "Check failed")

    @classmethod
    def check_api_key(cls, api_key: str) -> NoReturn:

        url = f"https://api.telegram.org/bot{api_key}/getMe"

        try:
            response = urllib.request.urlopen(url)
            data = json.load(response)

            if not data["ok"]:
                raise cls.ApiKeyCheckError("API-key's check failed")

        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            raise cls.ApiKeyCheckError(e) from e

        finally:
            logger.info("API-key's check passed")


    @classmethod
    def get_file_type(cls, packet: str) -> Tuple[str, str]:
        pass


    @staticmethod
    def guess_mime_type(file_input):
        if isinstance(file_input, BytesIO):
            # Additional logic for BytesIO objects might be required
            return 'application/octet-stream'
        else:
            mime_type, _ = mimetypes.guess_type(file_input)
            return mime_type if mime_type else 'application/octet-stream'



    def check_files(cls, packets: List[str]) -> NoReturn:

        fucked_up_packages = {}

        for packet in packets:

            if not os.path.exists(packet):
                fucked_up_packages[packet] = "File not found"

            elif not os.path.isfile(packet):
                fucked_up_packages[packet] = "Not a file"

            elif os.path.getsize(packet) == 0:
                fucked_up_packages[packet] = "File must be not empty"

            elif os.path.getsize(packet) > cls._MAX_SIZE:
                readable_size = Utilities.format_bytes(os.path.getsize(packet))
                fucked_up_packages[packet] = f"File must be less than 50 MB, this file is {readable_size}"

        if fucked_up_packages:
            error_message = "\n\t" + "\n\t".join([f"{key}: {value}" for key, value in fucked_up_packages.items()])
            raise cls.CheckError(error_message)


    @classmethod
    def check_audiofiles(cls, packets: List[str]) -> NoReturn:

        allowed_formats = ["mp3", "ogg", "wav"]

        fucked_up_packages = {}

        for packet in packets:

            if not os.path.exists(packet):
                fucked_up_packages[packet] = "File not found"

            elif not os.path.isfile(packet):
                fucked_up_packages[packet] = "Not a file"

            elif os.path.getsize(packet) == 0:
                fucked_up_packages[packet] = "File must be not empty"

            elif os.path.getsize(packet) > cls._MAX_SIZE:
                readable_size = format_bytes(os.path.getsize(packet))
                fucked_up_packages[packet] = f"File must be less than 50 MB, this file is {readable_size}"

            elif os.path.splitext(packet)[1] not in allowed_formats:
                fucked_up_packages[packet] = "File has unsupported extensions, must be one of " + ", ".join(allowed_formats)

        if fucked_up_packages:
            error_message = "\n\t" + "\n\t".join([f"{key}: {value}" for key, value in fucked_up_packages.items()])
            raise cls.CheckError(error_message)


    @classmethod
    def check_byte_string(cls, packets: List[BytesIO], size_limit: int) -> NoReturn:

        fucked_up_packages = {}

        for index, packet in enumerate(packets, start = 1):

            size = sys.getsizeof(packet)

            if not packet:
                fucked_up_packages[f"FileObject {index}"] = f"File is empty"

            elif size > cls._MAX_SIZE:
                readable_size = Utilities.format_bytes(size)
                fucked_up_packages[f"FileObject {index}"] = f"File must be less than 50 MB, this file is {readable_size}"

        if fucked_up_packages:
            error_message = "\n\t" + "\n\t".join([f"{key}: {value}" for key, value in fucked_up_packages.items()])
            raise cls.CheckError(error_message)


    @classmethod
    def check_open_files(cls, packets: BytesIO) -> bool:
        pass

class _TimeStamp:

    def key() -> str:
        return datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S_%f")

    def log() -> str:
        return datetime.datetime.now().strftime("%Y.%m.%d %H:%M:%S")


class _Interface:

    def confirmation_loop():
        pass

    def check_contacts():
        pass


def format_bytes(size: int) -> str:

    power = 2**10
    n = 0
    power_labels = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}

    while size > power:
        size /= power
        n += 1

    return f"{size:.2f} {power_labels[n]}"
