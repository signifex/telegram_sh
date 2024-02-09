# internet shit
import urllib.request
import urllib.parse
import urllib.error
import json
import socket
import uuid

# concurrenting execution stuff
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
from collections import deque

# other stuff and type hints
import os
import mimetypes
from io import BytesIO
from typing import List, Set, Dict, Tuple, Union, Optional, NoReturn

# local imports
from . import logger
from .utilities import _ModuleBaseException, _TimeStamp, _Utilities, Checkers


class Dispatcher:

    class FilesAmountError(_ModuleBaseException):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs, error_title="10 file per 1 message")

    class FilesTypeError(_ModuleBaseException):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs, error_title="Wrong file type")

    class FileProcessingError(_ModuleBaseException):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs, error_title="File pre-check failed")

    class DispatcherInitializationError(_ModuleBaseException):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs, error_title="An error occurred during initialization of the despatcher")

    _METHODS = {

        "document": {
            "api_method": "sendDocument",
            "mime_types": ["application/octet-stream"],
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
                 autoswitch_file_type: bool = False,
                 skip_invalid_files: bool = False,
                 extra_return: bool = False,
                 ) -> None:

        Checkers.check_api_key(api_key)

        if not all(isinstance(key, int) for key in recipients.keys()):
            error_message = "All recipeints must be represented" \
                "as a dictionary [int: str]. "\
                "Where int is a chat, associeted the with bot, " \
                "str for logging processes"

            raise self.DispatcherInitializationError(
                error_message=error_message)

        self.__base_url = f"https://api.telegram.org/bot{api_key}/"
        self.__thread_lock = Lock()
        self._api_key_name = api_key_name
        self._recipients = recipients
        self._logs = deque(maxlen=log_size * self._recipients_amount)
        self.print_status = print_status
        self.autoswitch_file_type = autoswitch_file_type
        self.skip_invalid_files = skip_invalid_files
        self.extra_return = extra_return

    def __repr__(self) -> str:
        return ("Dispatcher configurations:\n"
                f"  Name of API-key: {self._api_key_name}\n"
                f"  Amount of recipients: {self._recipients_amount}\n"
                f"  Logs cache: {len(self._logs)}/{self._logs.maxlen}\n"
                f"  Status printing: {self.print_status}\n"
                f"  Switch to document type instead of"\
                "raising an error: {self.autoswitch_file_type}\n"
                f"  Extra return for each printing log: {self.extra_return}")

    def __enter__(self, io_object):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    @property
    def _recipients_amount(self):
        return len(self._recipients)

    def send_message(self, message: str) -> None:

        if len(message) > 4096:
            raise ValueError("message is too long: max 4096 symbols per one message")

        message_url = self.__base_url + "sendMessage"

        with ThreadPoolExecutor() as executor:
            for recipient in self._recipients.items():
                executor.submit(self._execute_message_send,
                                message_url,
                                recipient,
                                message,
                                self._logs,
                                self.print_status,
                                self.extra_return,
                                self.__thread_lock)

    @staticmethod
    def _execute_message_send(message_url: str,
                              recipient: Tuple[int, str],
                              message: str,
                              logging_queue: deque,
                              print_status: bool,
                              extra_return: bool,
                              thread_lock: Lock
                              ) -> None:

        chat_id, chat_name = recipient[0], recipient[1]

        params = {"chat_id": chat_id, "text": message}

        data = urllib.parse.urlencode(params).encode("utf-8")

        key = _TimeStamp.log()
        description = (f"Message from: {key}; "
                       "recipient: {chat_id}; {chat_name}; ")

        try:
            with urllib.request.urlopen(message_url, data) as response:
                response_data = response.read().decode("utf-8")
                response_json = json.loads(response_data)

            if response_json.get("ok"):
                description += "Successfully delivered"

            else:
                error_description = response_json.get("description",
                                                      "Unknown error")
                description += f"Not delivered: {error_description}"

        except urllib.error.HTTPError as e:
            description += f"HTTP Error {e.code}: {e.reason}"

        except urllib.error.URLError as e:
            description += f"URL Error: {e.reason}"

        except socket.timeout:
            description += "Timeout Error: The request timed out"

        except Exception as e:
            description += f"General Error: {str(e)}"

        finally:

            with thread_lock:
                logging_queue.append(description)

                if print_status:

                    if extra_return:
                        description += "\n"

                    print(description)

    def send_file(self, files: Union[str, List[str], BytesIO, List[BytesIO]],
                  files_type: str = "document") -> None:

        if files_type not in self._METHODS:
            raise ValueError

        if isinstance(files, str) or isinstance(files, BytesIO):
            files = [files]

        checked_files, mime_types = self._check_files(files)

        sending_url = self.__base_url + self._METHODS[files_type]["api_method"]

        file_streams, mime_types = self._open_files(files, files_type)

        request_body = self._create_request_body(file_streams, mime_types)

        with ThreadPoolExecutor() as executor:

            futures = [executor.submit(self._execute_file_send,
                                       sending_url,
                                       recipient,
                                       request_body,
                                       self._logs,
                                       self.print_status,
                                       self.extra_return,
                                       self.__thread_lock
                                       )
                       for recipient in self._recipients.items()
                       ]

    @staticmethod
    def _execute_files_send(message_url: str, recipient: Tuple[int, str],
                            request_body: Tuple[str, str]) -> str:
        pass

    def _create_request_body(self,
                             provided_files: List[Union[str, BytesIO]],
                             mime_types: List[str],
                             files_type: str
                             ) -> Tuple[str, str]:

        if len(provided_files) != len(mime_types):
            error_message = "amounts of files and "\
                "their mime types are not equal"
            raise self.FilesAmountError(error_message=error_message)

        boundary = "----WebKitFormBoundary" + uuid.uuid4().hex

        headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
        data = []

        media = [{"type": files_type, "media": f"attach://file{i}"}
                 for i, _ in enumerate(provided_files)]
        data.append(f"--{boundary}")
        data.append("Content-Disposition: form-data; name='media'")
        data.append("Content-Type: application/json")
        data.append("")
        data.append(json.dumps(media))

        for i, (file_object, mime_type) in enumerate(zip(provided_files,
                                                         mime_types), start=1):

            data.append(f"--{boundary}")
            data.append(f"Content-Disposition: form-data; name='file{i}'; "
                        f"filename='file{i}'")
            data.append(f"Content-Type: {mime_type}")
            data.append("")

            if isinstance(file_object, str):
                with open(file_object, "rb") as file_obj:
                    data.append(file_obj.read().decode("iso-8859-1"))
            elif isinstance(file_object, BytesIO):
                data.append(file_obj.getvalue().decode("iso-8859-1"))

        data.append(f"--{boundary}--")
        data.append("")

        full_data = "\r\n".join(data).encode("iso-8859-1")
        return full_data, headers

    def _check_files(self,
                     provided_files: List[Union[str, BytesIO]],
                     sending_method: str
                     ) -> Tuple[List[Union[str, BytesIO]], List[str]]:

        checked_files = []
        mime_types = []
        invalid_files = {}
        max_file_size = self._METHODS[sending_method]["max_file_size"]
        allowed_mime_types = self._METHODS[sending_method]["mime_types"]

        for i, file_object in enumerate(provided_files, start=1):

            if isinstance(file_object, str):

                if not os.path.exists(file_object):
                    invalid_files[file_object] = "File not found"
                elif not os.path.isfile(file_object):
                    invalid_files[file_object] = "Not a file"
                elif os.path.getsize(file_object) == 0:
                    invalid_files[file_object] = "File must be not empty"
                elif os.path.getsize(file_object) > max_file_size:
                    readable_size = _Utilities.format_bytes(
                        os.path.getsize(file_object))
                    invalid_files[file_object] = "File must be less than" \
                        f"{max_file_size} bytes, this file is {readable_size}"
                elif sending_method == "document":
                    mime_type = self._METHODS["document"]["mime_types"]
                    mime_types.append(mime_type)
                    checked_files.append(file_object)
                else:
                    mime_type, _ = mimetypes.guess_type(file_object)
                    if mime_type is None:
                        invalid_files[file_object] = "Cannot determine MIME type"
                    elif mime_type not in allowed_mime_types:
                        error_message = (f"File type {mime_type} "
                                         f"is not allowed by Telegram for {sending_method}")
                        invalid_files[file_object] = error_message
                    else:
                        mime_types.append(mime_type)
                        checked_files.append(file_object)

            elif isinstance(file_object, BytesIO):

                file_object.seek(0, os.SEEK_END)
                file_size = file_object.tell()
                file_object.seek(0)

                if file_size == 0:
                    invalid_files[f"File object #{i}"] = "File must be not empty"

                elif file_size > self._METHODS["document"]["max_file_size"]:
                    readable_size = _Utilities.format_bytes(file_size)
                    error_message = (f"File must be less than {max_file_size} "
                                     f"bytes, this file is {readable_size}")
                    invalid_files[f"Open file {i}"] = error_message

                mime_type = self._METHODS["document"]["api_method"]
                checked_files.append(file_object)
                mime_types.append(mime_type)

            if invalid_files:
                errors_list = [f"{key}: {value}"
                               for key, value in invalid_files.items()]

                error_message = "\n\t" + "\n\t".join(errors_list)
                if self.skip_invalid_files:
                    print(error_message)
                else:
                    raise self.FileProcessingError(error_message=error_message)

            return checked_files, mime_types


    # def _check_files(self, file_paths: List[str], sending_method) -> Tuple[List[str], List[str]]:

    #     checked_files = []
    #     mime_types = []
    #     invalid_files = {}
    #     max_file_size = self._METHODS[sending_method]["max_file_size"]
    #     allowed_mime_types = self._METHODS[sending_method]["mime_types"]

    #     for file_path in file_paths:

    #         if not os.path.exists(file_path):
    #             invalid_files[file_path] = "File not found"
    #         elif not os.path.isfile(file_path):
    #             invalid_files[file_path] = "Not a file"
    #         elif os.path.getsize(file_path) == 0:
    #             invalid_files[file_path] = "File must be not empty"
    #         elif os.path.getsize(file_path) > max_file_size:
    #             readable_size = _Utilities.format_bytes(os.path.getsize(file_path))
    #             invalid_files[file_path] = f"File must be less than {max_file_size} bytes, this file is {readable_size}"

    #         else:
    #             mime_type, _ = mimetypes.guess_type(file_path)
    #             if mime_type is None and sending_method != "document":
    #                 invalid_files[file_path] = "Cannot determine MIME type"
    #             elif mime_type not in allowed_mime_types:
    #                 invalid_files[file_path] = f"File type {mime_type} is not allowed by Telegram for {sending_method}"
    #             else:
    #                 mime_types.append(mime_type)
    #                 checked_files.append(file_path)

    #     if invalid_files:
    #         error_message = "\n\t" + "\n\t".join([f"{key}: {value}" for key, value in invalid_files.items()])
    #         raise self.FileProcessingError(error_message=error_message)

    #     return checked_files, mime_types


    # def _sync_file_handler(self,
    #                        packets: List[str],
    #                        as_doc: bool = False,
    #                        caption: Optional[str] = None
    #                        ) -> str:

    #     if packet_type == "audiofiles":
    #         url = f"https://api.telegram.org/bot{self.api_key}/sendAudio"

    #     else:
    #         url = f"https://api.telegram.org/bot{self.api_key}/sendDocument"

    #     open_files = [("document", open(packet, "rb")) for packet in packets]

    #     tasks = [self._files_dispatcher(url, open_files, recipient_id, recipient_name, caption)
    #              for recipient_id, recipient_name in self.recipients.items()
    #              ]



    # async def _files_dispatcher(self,
    #                             url: str,
    #                             open_files: List[BinaryIO],
    #                             recipient_id: int,
    #                             recipient_name: str,
    #                             caption: Optional[str]
    #                             ) -> NoReturn:

    #     data = {"chat_id": recipient_id}

    #     if caption:
    #         data["caption"] = caption

    #     response = await requests.post(url, data = data, files = open_files)

    #     key = Utilities.key_timestamp()

    #     if response.status_code == 200:
    #        self._sending_success[key] =  f"recipient: {recipient_id}/{recipient_name}"

    #     else:
    #        description = f"recipient: {recipient_id}/{recipient_name}\n" + str(json.loads(response.content)["description"])
    #        self._sending_errors[key] = description



    # def send_audiofiles(self, packets: List[str]) -> str:

    #     cls.check_audiofiles(packets = packets)

    #     checksum = len(self.recipients) * len(packets)

    #     asyncio.run(self._file_handler(packets = packets, p_type = "audiofiles"))

    #     return SendingStatus(success = self._sending_success, fail = self._sending_errors, checksum = checksum)
