import urllib.request, urllib.parse, urllib.error
import json
import socket

import asyncio
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
from collections import deque

from io import BytesIO
from typing import List, Set, Dict, Tuple, NamedTuple, Literal, Union, Iterable, BinaryIO, Optional, NoReturn

from . import logger
from .utilities import _ModuleBaseException, _TimeStamp

import sys

class Dispatcher:

    class MissedModuleError(_ModuleBaseException):
        def __init__(*args, **kwargs):
            super().__init__(*args, **kwargs, error_title = "Module 'aiohttp' or 'requests' is required to send files")

    class FilesAmountError(_ModuleBaseException):
        def __init__(*args, **kwargs):
            super().__init__(*args, **kwargs, error_title = "Currently unable to send this type of message")

    class DispatcherInitializationError(_ModuleBaseException):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs, error_title = "An error occurred during initialization of the despatcher")

    class FileCheckFailed(_ModuleBaseException):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs, error_name = "Check failed")

    class ApiKeyCheckFailed(_ModuleBaseException):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs, error_name = "Check failed")

    _methods = {

    "document": {
        "api_method": "sendDocument",
        "mime_types": ["any"],
        "supporting_formats": ["any"],
        "max_file_size": 50 * 1024 * 1024,
        "max_files_amount": 10
    },

    "photo": {
        "api_method": "sendPhoto",
        "mime_types": ["image/jpeg", "image/png"],
        "supporting_formats": [".jpg", ".jpeg", ".png"],
        "max_file_size": 10 * 1024 * 1024,
        "max_files_amount": 10
    },

    "audio": {
        "api_method": "sendAudio",
        "mime_types": ["audio/mpeg", "audio/mp3"],
        "supporting_formats": [".mp3", ".mpeg"],
        "max_file_size": 50 * 1024 * 1024,
        "max_files_amount": 10
    },

    "video": {
        "api_method": "sendVideo",
        "mime_types": ["video/mp4", "video/quicktime"],
        "supporting_formats": [".mp4", ".mov"],
        "max_file_size": 50 * 1024 * 1024,
        "max_files_amount": 10
    },

    "animation": {
        "api_method": "sendAnimation",
        "mime_types": ["video/mp4", "video/quicktime"],
        "supporting_formats": [".mp4", ".gif"],
        "max_file_size": 50 * 1024 * 1024,
        "max_files_amount": 1
    },

    "voice": {
        "api_method": "sendVoice",
        "mime_types": ["audio/ogg", "audio/mpeg"],
        "supporting_formats": [".ogg", ".mp3"],
        "max_file_size": 50 * 1024 * 1024,
        "max_files_amount": 1
    },

    "video_note": {
        "api_method": "sendVideoNote",
        "mime_types": ["video/mp4"],
        "supporting_formats": [".mp4"],
        "max_file_size": 50 * 1024 * 1024,
        "max_files_amount": 1
    },

    "sticker": {
        "api_method": "sendSticker",
        "mime_types": ["image/webp"],
        "supporting_formats": [".webp"],
        "max_file_size": 512 * 1024,
        "max_files_amount": 1
    }
    }


    def __init__(self,
                 api_key: str,
                 api_key_name: str,
                 recipients: Dict[int, str],
                 log_size: int = 10,
                 print_status: bool = True,
                 ) -> None:

        self.check_api_key(api_key)

        if not all(isinstance(key, int) for key in recipients.keys()):
            raise self.DispatcherInitializationError("All recipeints must be represented as a dictionary [int: str]. "
                                                     "Where int is a chat, associeted the with bot, str for logging processes")

        self.__base_url = f"https://api.telegram.org/bot{api_key}/"
        self.__thread_lock = Lock()
        self._api_key_name = api_key_name
        self._recipients = recipients
        self._recipients_amount = len(recipients)
        self._logs = deque(maxlen = log_size * self._recipients_amount)
        self.print_status = print_status

    def __repr__(self) -> str:
        return ("Dispatcher configurations:\n"
                f"  Name of API-key: {self._api_key_name}\n"
                f"  Amount of recipients: {self._recipients_amount}\n"
                f"  Logs chache: {len(self._logs)}/{self._logs.maxlen}\n"
                f"  Status printing: {self.print_status}")

    def __enter__(self, io_object):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        pass


    def send_message(self, message: str) -> None:

        if len(message) > 4096:
            raise ValueError("message is too long: max 4096 symbols per one message")

        message_url = self.__base_url + "sendMessage"


        with ThreadPoolExecutor() as executor:

            futures = [executor.submit(self._execute_message_send,
                                       message_url,
                                       recipient,
                                       message,
                                       self._logs,
                                       self.print_status,
                                       self.__thread_lock
                                       )
                       for recipient in self._recipients.items()
                       ]

    @staticmethod
    def _execute_message_send(message_url: str,
                              recipient: Tuple[int, str],
                              message: str,
                              logging_queue: deque,
                              print_status: bool,
                              thread_lock: Lock
                              ) -> None:

        chat_id, chat_name = recipient[0], recipient[1]

        params = {"chat_id": chat_id, "text": message}

        data = urllib.parse.urlencode(params).encode("utf-8")

        key = _TimeStamp.log()

        try:
            with urllib.request.urlopen(message_url, data) as response:
                response_data = response.read().decode("utf-8")
                response_json = json.loads(response_data)

            if response_json.get("ok"):
                description = f"Message from {key}, recipient: {chat_id}; {chat_name}, successfully delivered"

            else:
                error_description = response_json.get("description", "Unknown error")
                description = f"Message from {key}, recipient: {chat_id}; {chat_name}, not delivered: {error_description}"

        except urllib.error.HTTPError as e:
            description = f"Message from {key}, recipient: {chat_id}; {chat_name}, not delivered: HTTP Error {e.code} - {e.reason}"

        except urllib.error.URLError as e:
            description = f"Message from {key}, recipient: {chat_id}; {chat_name}, not delivered: URL Error - {e.reason}"

        except socket.timeout:
            description = f"Message from {key}, recipient: {chat_id}; {chat_name}, not delivered: Timeout Error - The request timed out"

        except Exception as e:
            description = f"Message from {key}, recipient: {chat_id}; {chat_name}, not delivered: General Error - {str(e)}"

        finally:
            with thread_lock:
                logging_queue.append(description)
                if print_status:
                    print(description + "\n")
                    ## \n for bpython, overvise its will join description with own new line symbol ">>>"
                    ## so mb just add a flag, to overvise it

    def send_file(self, packets: Union[str, list[str]], packets_type: str = "doc") -> None:

        pass

        # if isinstance(packets, str):
        #     packets = [packets]

        # for packet in packets:


    def send_open_file(self, packets: Union[BytesIO, list[BytesIO]], packets_type: str = "doc") -> None:
        if isinstance(packets, BytesIO):
            packets = [packets]

    @staticmethod
    def _execute_files_send(message_url: str, recipient: Tuple[int, str], message: str) -> str:
        pass

    def _create_request_body(self, media_files: List[BytesIO], files_type: str) -> Tuple[str, str]:

        if len(media_files) > 10:
             raise self.FilesAmoutError(f"Number of media files exceeds the maximum limit of 10")

        boundary = "----WebKitFormBoundary" + uuid.uuid4().hex

        headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
        data = []

        media = [{"type": files_type, "media": f"attach://file{i}"} for i, _ in enumerate(media_files)]
        data.append(f"--{boundary}")
        data.append("Content-Disposition: form-data; name='media'")
        data.append("Content-Type: application/json")
        data.append("")
        data.append(json.dumps(media))

        for i, file_obj in enumerate(media_files):
            mime_type = "application/octet-stream"
            data.append(f"--{boundary}")
            data.append(f"Content-Disposition: form-data; name='file{i}'; filename='file{i}'")
            data.append(f"Content-Type: {mime_type}")
            data.append("")
            data.append(file_obj.getvalue().decode("iso-8859-1"))

        data.append(f"--{boundary}--")
        data.append("")

        full_data = "\r\n".join(data).encode("iso-8859-1")
        return full_data, headers


    def _sync_file_handler(self,
                           packets: List[str],
                           as_doc: bool = False,
                           caption: Optional[str] = None
                           ) -> str:

        if packet_type == "audiofiles":
            url = f"https://api.telegram.org/bot{self.api_key}/sendAudio"

        else:
            url = f"https://api.telegram.org/bot{self.api_key}/sendDocument"

        open_files = [("document", open(packet, "rb")) for packet in packets]

        tasks = [self._files_dispatcher(url, open_files, recipient_id, recipient_name, caption)
                 for recipient_id, recipient_name in self.recipients.items()
                 ]



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

        key = Utilities.key_timestamp()

        if response.status_code == 200:
           self._sending_success[key] =  f"recipient: {recipient_id}/{recipient_name}"

        else:
           description = f"recipient: {recipient_id}/{recipient_name}\n" + str(json.loads(response.content)["description"])
           self._sending_errors[key] = description



    def send_audiofiles(self, packets: List[str]) -> str:

        cls.check_audiofiles(packets = packets)

        checksum = len(self.recipients) * len(packets)

        asyncio.run(self._file_handler(packets = packets, p_type = "audiofiles"))

        return SendingStatus(success = self._sending_success, fail = self._sending_errors, checksum = checksum)


    @staticmethod
    def check_api_key(api_key: str) -> NoReturn:

        url = f"https://api.telegram.org/bot{api_key}/getMe"

        try:
            response = urllib.request.urlopen(url)
            data = json.load(response)

            if not data["ok"]:
                raise cls.ApiKeyCheckFailed("API-key's check failed")

        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            raise cls.ApiKeyCheckFailed(e) from e

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
            raise cls.CheckFailed(error_message)


    @classmethod
    def check_open_files(cls, packets: BytesIO) -> bool:
        pass

    # @classmethod
    # def check_audiofiles(cls, packets: List[str]) -> NoReturn:

    #     allowed_formats = ["mp3", "ogg", "wav"]

    #     fucked_up_packages = {}

    #     for packet in packets:

    #         if not os.path.exists(packet):
    #             fucked_up_packages[packet] = "File not found"

    #         elif not os.path.isfile(packet):
    #             fucked_up_packages[packet] = "Not a file"

    #         elif os.path.getsize(packet) == 0:
    #             fucked_up_packages[packet] = "File must be not empty"

    #         elif os.path.getsize(packet) > cls._MAX_SIZE:
    #             readable_size = format_bytes(os.path.getsize(packet))
    #             fucked_up_packages[packet] = f"File must be less than 50 MB, this file is {readable_size}"

    #         elif os.path.splitext(packet)[1] not in allowed_formats:
    #             fucked_up_packages[packet] = "File has unsupported extensions, must be one of " + ", ".join(allowed_formats)

    #     if fucked_up_packages:
    #         error_message = "\n\t" + "\n\t".join([f"{key}: {value}" for key, value in fucked_up_packages.items()])
    #         raise cls.CheckFailed(error_message)


    # @classmethod
    # def check_byte_string(cls, packets: List[BytesIO], size_limit: int) -> NoReturn:

    #     fucked_up_packages = {}

    #     for index, packet in enumerate(packets, start = 1):

    #         size = sys.getsizeof(packet)

    #         if not packet:
    #             fucked_up_packages[f"FileObject {index}"] = f"File is empty"

    #         elif size > cls._MAX_SIZE:
    #             readable_size = Utilities.format_bytes(size)
    #             fucked_up_packages[f"FileObject {index}"] = f"File must be less than 50 MB, this file is {readable_size}"

    #     if fucked_up_packages:
    #         error_message = "\n\t" + "\n\t".join([f"{key}: {value}" for key, value in fucked_up_packages.items()])
    #         raise cls.CheckFailed(error_message)

