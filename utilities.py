"""
module utils:

ModuleBaseException - main exeption of the class,
 make able to catch all modules exeption but nothing else

_callableClassMeta let class return not itself by call,
 but execute some fuction, to make code more "plain"

Checkers - collection of pre-sening methods to check,
that telegram api call will be valid,
but files checkers are moved to dispatcher, so mb ill return it back
or delete this one

_TimeStamp return a string to make unique key for or logging-freindly time

etc
"""
import traceback
import datetime
import urllib.request
import json

from typing import Optional, NoReturn

from . import logger

try:
    from decorations import Colorize
    _COLORIZE = True
except ImportError:
    _COLORIZE = False


class ModuleBaseException(Exception):
    """
    Base exception class to provide a consistent format for custom exceptions.

    This class is designed to be subclassed and should not be raised directly.
    ModuleBaseException is the foundational exception class for custom
    exceptions in this module.

    It's designed to capture and store detailed information about exceptions,
    making it easier to handle, log, and report errors. Child exceptions
    derived from this class can provide more specific error contexts
    or messages.

    Attributes:
    original_exception (Exception):
       The original exception that triggered the custom exception.
       If no original exception is provided,
       it defaults to the custom exception itself.

    name (str): Name of the exception, typically the class name.
    message (str): Detailed message of the error
    (or default error's message, will overwrite error's default message!)
    traceback (str): Stack trace of the error.
    log (str): Log message that combines the timestamp, error name,
    message, and traceback.

    Usage:
    This class is intended to be subclassed for specific exception types
    and should not be raised directly. When creating a child exception,
    provide the original exception and an optional custom message to the
    initializer. When handling the exception, you can access its attributes
    for custom error reporting or logging.

    Example:
    ...
    class CustomError(ModuleBaseException):
        def __init__(self, *args, **kwargs)
            super().__init__(*args, **kwargs,
                             error_title = "more functional name")
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

    def __init__(self,
                 original_exception: Optional[Exception] = None,
                 error_title: Optional[str] = None,
                 error_message: Optional[str] = None):

        if self.__class__ == ModuleBaseException:
            error_message = "ModuleBaseException should not be "\
                "raised directly. Use a child class instead."
            raise NotImplementedError(error_message)

        self.original_exception = original_exception \
            if original_exception else self

        self.title = error_title if error_title else self.__class__.__name__

        self.message = str(self.original_exception) \
            if original_exception else error_message

        if isinstance(original_exception, Exception):
            self.traceback = traceback.format_exception(
                type(original_exception),
                original_exception,
                original_exception.__traceback__)

        else:
            self.traceback = traceback.format_stack()[:-2]

        self.log = "\n".join(("\n" + _TimeStamp.log(),
                              self.__str__(), ''.join(self.traceback)))

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

    def __new__(mcs, name, bases, namespace, class_call_method):

        if class_call_method not in namespace:
            error_message = f"'{class_call_method}' method not found in {name}"
            raise AttributeError(error_message)

        cls = super().__new__(mcs, name, bases, namespace)

        cls.__class_call_method = namespace[class_call_method]

        if not callable(cls.__class_call_method):
            error_message = (f"'{class_call_method}' must be a "
                             f"callable method in {name}")
            raise AttributeError(error_message)

        return cls

    def __call__(cls, *args, **kwargs):
        return cls.__class_call_method(*args, **kwargs)


class Checkers:
    """
    global checkers...

    to make sure, thats all part of the script will work as needed
    """
    class ApiKeyCheckError(ModuleBaseException):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs,
                             error_name="Check failed")

    @classmethod
    def check_api_key(cls, api_key_value: str) -> NoReturn:

        url = f"https://api.telegram.org/bot{api_key_value}/getMe"

        try:
            response = urllib.request.urlopen(url)
            data = json.load(response)

            if not data["ok"]:
                raise cls.ApiKeyCheckError("API-key's check failed")

        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            raise cls.ApiKeyCheckError(e) from e

        finally:
            logger.info("API-key's check passed")


class _TimeStamp:

    @staticmethod
    def key() -> str:
        """
        return time as unique key: "%Y_%m_%d_%H_%M_%S_%f"
        """
        return datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S_%f")

    @staticmethod
    def log() -> str:
        """
        return key for logging: "%Y.%m.%d %H:%M:%S"
        """
        return datetime.datetime.now().strftime("%Y.%m.%d %H:%M:%S")


class _Interface:


    def confirmation_loop(self):
        pass

    def check_contacts(self):
        pass


class _MessageFormater:

    def __init__(self,
                 use_colorize: bool,
                 extra_return: bool
                 ):
        """
        Set up an output message builder...

        use_colorize - If decorations.Colrize is able to import,
        and this flag is set to True, output messages will be formated
        """

        self.use_colorize = use_colorize
        self.extra_return = extra_return
        self.raw_data_storage = []

    def add_text(self, text: str, **editing_args):
        """
        add text to message chain

        kwargs are reffer to Colorize arguments
        """
        editing_text = {"text": text}
        editing_text.update(editing_args)
        self.raw_data_storage.append(editing_text)
        return self

    @property
    def colorized_text(self):
        """
        main method to create a colored sting
        (if possible)
        """

        if _COLORIZE and self.use_colorize:
            full_message = ""
            for part in self.raw_data_storage:
                formatted_text = str(Colorize(**part))
                full_message += formatted_text
            if self.extra_return:
                full_message += "\n"
        else:
            full_message = self.raw_text

        return full_message

    @property
    def raw_text(self):
        """
        return simply chined text.

        for logger or when Colorize is not found or turned off
        """
        full_message = ''.join(part["text"] for part
                               in self.raw_data_storage)
        if self.extra_return:
            full_message += "\n"

        return full_message


class _Utilities:

    @staticmethod
    def format_bytes(size: int) -> str:

        power = 2**10
        n = 0
        power_labels = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}

        while size > power:
            size /= power
            n += 1

        return f"{size:.2f} {power_labels[n]}"
