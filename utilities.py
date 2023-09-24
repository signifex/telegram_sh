import traceback
import datetime
import urllib.request

from io import BytesIO
from typing import Dict, List, Tuple, BinaryIO, Optional, Iterable, NoReturn

from . import logger

class ModuleBaseException(Exception):

    """
    Base exception class to provide a consistent format for custom exceptions.
    This class is designed to be subclassed and should not be raised directly.

    ModuleBaseException is the foundational exception class for custom exceptions in this module.

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
            class CustomError(ModuleBaseException):
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
            raise NotImplementedError("ModuleBaseException should not be raised directly. Use a subclass instead.")

        self.original_exception = original_exception if original_exception else self

        self.title = error_title if error_title else self.__class__.__name__

        self.message = str(self.original_exception) if original_exception else error_message

        if isinstance(original_exception, Exception):
            self.traceback = traceback.format_exception(type(original_exception), original_exception, original_exception.__traceback__)
        else:
            self.traceback = traceback.format_stack()[:-2]

        self.log = "\n".join(("\n" + normal_timestamp(), self.__str__(), ''.join(self.traceback)))

        logger.error(self.log)

        super().__init__(self.message)

    def __str__(self):
        return f"{self.title}: {self.message}"


class SimpeInterface:

    def confirmation_loop():
        pass

    def check_contacts():
        pass


class Checkers:

    _MAX_SIZE = 50 * 1024 * 1024

    class CheckFailed(ModuleBaseException):
        def __init__(self, *args):
            super().__init__(*args, error_name = "Check failed")

    @classmethod
    def check_api_key(cls, api_key: str) -> NoReturn:
        url = f"https://api.telegram.org/bot{api_key}/getMe"

        try:
            response = urllib.request.urlopen(url)
            data = json.load(response)

            if not data["ok"]:
                raise cls.CheckFailed("API-key's check failed")

        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            raise Utilities.Checkers.CheckFailed(e) from e

        finally:
            logger.info("API-key's check passed")


    @classmethod
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
            raise Utilities.Checkers.CheckFailed(error_message)


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
                readable_size = Utilities.format_bytes(os.path.getsize(packet))
                fucked_up_packages[packet] = f"File must be less than 50 MB, this file is {readable_size}"

            elif os.path.splitext(packet)[1] not in allowed_formats:
                fucked_up_packages[packet] = "File has unsupported extensions, must be one of " + ", ".join(allowed_formats)

        if fucked_up_packages:
            error_message = "\n\t" + "\n\t".join([f"{key}: {value}" for key, value in fucked_up_packages.items()])
            raise Utilities.Checkers.CheckFailed(error_message)


    @classmethod
    def check_byte_string(cls, packets: List[BytesIO]) -> NoReturn:

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
            raise Utilities.Checkers.CheckFailed(error_message)


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
                 api_key_value: str,
                 recipients: Iterable[int],
                 api_key_name: Optional[str] = None):

        self._api_key_value = api_key_value
        self.api_key_name = api_key_name
        self._recipients = recipients.copy() if isinstance(recipients, dict) else dict.fromkeys(recipients)

        logger.info(f"Data for sending messages is formed, amount of recipients: {len(self._recipients)}")


    def _get_api_key(self) -> Tuple[str, str]:
        return self._api_key_value, self.api_key_name

    api_key_value = property(_get_api_key)


    def _get_recipients(self) -> Dict:
        return self._recipients

    recipients = property(_get_recipients)


    def manual_api_key(self, new_api_key: str):
        '''
        Provide API-key value manually.
        Will raise an error, if value of API-key is already set.
        '''
        if api_key_value:
            error = f"Replacing an existing api-key is not possible"
            raise AttributeError(error)

        else:
            self._api_key_value = new_api_key

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


def key_timestamp() -> str:
    return datetime.datetime.now().strftime("%Y_%m_%d_%H_%M_%S_%f")


def normal_timestamp() -> str:
    return datetime.datetime.now().strftime("%Y.%m.%d %H:%M:%S")


def format_bytes(size: int) -> str:

    power = 2**10
    n = 0
    power_labels = {0: 'B', 1: 'KB', 2: 'MB', 3: 'GB', 4: 'TB'}

    while size > power:
        size /= power
        n += 1

    return f"{size:.2f} {power_labels[n]}"

