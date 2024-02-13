# internet shit
import urllib.request
import urllib.parse
import urllib.error
import http.client
import json
import socket
import uuid

# concurrenting execution stuff
import threading
from concurrent.futures import ThreadPoolExecutor
from collections import deque

# other stuff and type hints
import os
import mimetypes
from io import BytesIO
from typing import List, Dict, Tuple, Union, Optional, NoReturn

# local imports
from . import logger
from .utilities import (_ModuleBaseException,
                        _TimeStamp,
                        _Utilities,
                        _MessageFormater,
                        Checkers)


class Dispatcher:

    """
    Main class of the script...

    takes arguments to configurate a dispatcher and will use methods
    send_message and send_file as public methods to dispatch it to
    configurated recipients concurrently
    """

    class FilesAmountError(_ModuleBaseException):
        def __init__(self, *args, **kwargs):
            error_title = "This amount of files is not able to this "\
                    "sending method"
            super().__init__(error_title=error_title,
                             *args, **kwargs )

    class FilesTypeError(_ModuleBaseException):
        def __init__(self, *args, **kwargs):
            super().__init__(error_title="Wrong file type",
                             *args, **kwargs)

    class FileProcessingError(_ModuleBaseException):
        def __init__(self, *args, **kwargs):
            error_title = "Pre-check of the files failed"
            super().__init__(error_title=error_title,
                             *args, **kwargs)

    class DispatcherInitializationError(_ModuleBaseException):
        def __init__(self, *args, **kwargs):
            error_title = "An error occurred during initialization "\
                    "of the despatcher"
            super().__init__(error_title=error_title,
                             *args, **kwargs)

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
                 api_key_value: str,
                 api_key_name: str,
                 recipients: Dict[int, str],
                 print_status: Optional[bool] = True,
                 **kwargs):

        Checkers.check_api_key(api_key_value)

        if not all(isinstance(key, int) for key in recipients.keys()):
            error_message = "All recipeints must be represented " \
                "as a dictionary [int: str]. "\
                "Where int is a chat, associeted the with bot, " \
                "str is any string for logging (name of the chat for example)"

            raise self.DispatcherInitializationError(
                error_message=error_message)

        if not all(len(value) < 64 for value in recipients.values()):
            error_message = "Max len is 64 chars for values in recipients dict"
            raise self.DispatcherInitializationError(
                error_message=error_message)

        self.__base_url = f"https://api.telegram.org/bot{api_key_value}/"
        self.__thread_lock = threading.Lock()
        self._api_key_name = api_key_name
        self._recipients = recipients
        self.print_status = print_status

        self._logs = deque(maxlen=self._recipients_amount *
                           kwargs.get("log_size", 10))

        self.autoswitch_file_type = kwargs.get("autoswitch_file_type", False)
        self.skip_invalid_files = kwargs.get("skip_invalid_files", False)

        self._message_formater_args = {
            "extra_return": kwargs.get("extra_return", False),
            "use_colorize": kwargs.get("use_colorize", True)
        }

    def __repr__(self) -> str:
        return ("Dispatcher configurations:\n"
                f"  Name of API-key: {self._api_key_name}\n"
                f"  Amount of recipients: {self._recipients_amount}\n"
                f"  Logs cache: {len(self._logs)}/{self._logs.maxlen}\n"
                f"  Status printing: {self.print_status}\n"
                "  Switch to document type instead of raising an error:"
                f" {self.autoswitch_file_type}")

    @property
    def _recipients_amount(self):
        return len(self._recipients)

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def send_message(self, message: str) -> NoReturn:
        """
        send message to all recipients

        max len 4096 chars
        """

        if len(message) > 4096:
            error_message = "message is too long: "\
                "max 4096 symbols per one message"
            raise ValueError(error_message)

        message_url = self.__base_url + "sendMessage"

        # for getting errors from threads

        # with ThreadPoolExecutor() as executor:
        #     futures = [executor.submit(self._execute_message_send,
        #                                message_url,
        #                                recipient,
        #                                message,
        #                                self._logs,
        #                                self.print_status,
        #                                self.__message_formater_args,
        #                                self.__thread_lock)
        #                for recipient in self._recipients.items()]

        # for future in futures:
        #     print(future.result())

        with ThreadPoolExecutor() as executor:
            for recipient in self._recipients.items():
                executor.submit(self._execute_message_send,
                                message_url=message_url,
                                recipient=recipient,
                                message=message)

    def _execute_message_send(self,
                              message_url: str,
                              recipient: Tuple[int, str],
                              message: str,
                              ) -> None:

        params = {"chat_id": recipient[0], "text": message}

        data = urllib.parse.urlencode(params).encode("utf-8")

        message_formater = _MessageFormater(**self._message_formater_args)

        message_formater.add_text("Message from: ")\
            .add_text(_TimeStamp.log(), bold=True)\
            .add_text(" Recipient: ")\
            .add_text(str(recipient[0]), bold=True)\
            .add_text("; ")\
            .add_text(recipient[1], bold=True)\
            .add_text("; Status: ")

        try:
            with urllib.request.urlopen(message_url, data) as response:
                response_data = response.read().decode("utf-8")
                response_json = json.loads(response_data)

            if response_json.get("ok"):
                message_formater.add_text("Successfully delivered",
                                          color="green", bold=True)

            else:
                error_description = response_json.get("description",
                                                      "Unknown error")

                message_formater.add_text("Not delivered: ",
                                          bold=True, color="red")\
                    .add_text(error_description)

        except urllib.error.HTTPError as e:
            message_formater.add_text(f"HTTP Error {e.code}",
                                      color="red", bold=True)\
                .add_text(": ")\
                .add_text(e.reason)

        except urllib.error.URLError as e:
            message_formater.add_text("URL Error", color="red", bold=True)\
                .add_text(": ")\
                .add_text(e.reason)

        except socket.timeout:
            message_formater.add_text("Timeout Error: The request timed out",
                                      color="red")

        except Exception as e:
            message_formater.add_text("General Error",
                                      color="red", bold=True)\
                .add_text(": ")\
                .add_text(str(e))

        finally:

            with self.__thread_lock:
                self._logs.append(message_formater.raw_text)

                if self.print_status:
                    print(message_formater.colorized_text)

    def send_file(self,
                  files: Union[str, List[str], BytesIO, List[BytesIO]],
                  files_type: str = "document") -> None:

        if files_type not in self._METHODS:
            raise ValueError

        if isinstance(files, str) or isinstance(files, BytesIO):
            files = [files]
            print("switched to list")

        checked_files, mime_types = self._check_files(files_list=files,
                                                      files_type=files_type)

        print("files checked")

        request_url = self.__base_url + self._METHODS[files_type]["api_method"]

        request_body, request_headers = self._create_request_body(
            files_list=checked_files,
            mime_types=mime_types,
            files_type=files_type)

        print("body created")

        with ThreadPoolExecutor() as executor:
            for recipient in self._recipients.items():
                executor.submit(self._execute_files_send,
                                request_url=request_url,
                                recipient=recipient,
                                request_body=request_body,
                                request_headers=request_headers)

    def _execute_files_send(self,
                            request_url: str,
                            recipient: Tuple[int, str],
                            request_body: str,
                            request_headers: str
                            ) -> NoReturn:

        pass

    def _check_files(self,
                     files_list: List[Union[str, BytesIO]],
                     files_type: str
                     ) -> Tuple[List[Union[str, BytesIO]], List[str]]:

        checked_files = []
        mime_types = []
        invalid_files = {}
        max_file_size = self._METHODS[files_type]["max_file_size"]
        allowed_mime_types = self._METHODS[files_type]["mime_types"]

        for i, f_obj in enumerate(files_list, start=1):

            if isinstance(f_obj, str):

                if not os.path.exists(f_obj):
                    invalid_files[f_obj] = "File not found"
                elif not os.path.isfile(f_obj):
                    invalid_files[f_obj] = "Not a file"
                elif os.path.getsize(f_obj) == 0:
                    invalid_files[f_obj] = "File must be not empty"
                elif os.path.getsize(f_obj) > max_file_size:
                    readable_size = _Utilities.format_bytes(
                        os.path.getsize(f_obj))
                    invalid_files[f_obj] = "File must be less than" \
                        f"{max_file_size} bytes, this file is {readable_size}"
                elif files_type == "document":
                    mime_type = self._METHODS["document"]["mime_types"]
                    mime_types.append(mime_type)
                    checked_files.append(f_obj)
                else:
                    mime_type, _ = mimetypes.guess_type(f_obj)
                    if mime_type is None:
                        invalid_files[f_obj] = "Cannot determine MIME type"
                    elif mime_type not in allowed_mime_types:
                        error_message = (f"File type {mime_type} "
                                         "is not allowed by Telegram for "
                                         f"{files_type}")
                        invalid_files[f_obj] = error_message
                    else:
                        mime_types.append(mime_type)
                        checked_files.append(f_obj)

            elif isinstance(f_obj, BytesIO):

                f_obj.seek(0, os.SEEK_END)
                file_size = f_obj.tell()
                f_obj.seek(0)

                if file_size == 0:
                    invalid_files[f"File object #{i}"] = "File is empty"

                elif file_size > self._METHODS["document"]["max_file_size"]:
                    readable_size = _Utilities.format_bytes(file_size)
                    error_message = (f"File must be less than {max_file_size} "
                                     f"bytes, this file is {readable_size}")
                    invalid_files[f"Open file {i}"] = error_message

                mime_type = self._METHODS["document"]["api_method"]
                checked_files.append(f_obj)
                mime_types.append(mime_type)

            if invalid_files:
                errors_list = [f"{key}: {value}"
                               for key, value in invalid_files.items()]

                error_message = "\n\t" + "\n\t".join(errors_list)
                if self.skip_invalid_files:
                    print(error_message)
                else:
                    raise self.FileProcessingError(
                        error_message=error_message)

            return checked_files, mime_types

    def _create_request_body(self,
                             files_list: List[Union[str, BytesIO]],
                             mime_types: List[str],
                             files_type: str
                             ) -> Tuple[str, str]:

        if len(files_list) != len(mime_types):
            error_message = "amounts of files and "\
                "their mime types are not equal"
            raise self.FilesAmountError(error_message=error_message)

        boundary = "----WebKitFormBoundary" + uuid.uuid4().hex

        headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
        data = []

        media = [{"type": files_type, "media": f"attach://file{i}"}
                 for i, _ in enumerate(files_list)]
        data.append(f"--{boundary}")
        data.append("Content-Disposition: form-data; name='media'")
        data.append("Content-Type: application/json")
        data.append("")
        data.append(json.dumps(media))

        for i, (file_object, mime_type) in enumerate(
                zip(files_list, mime_types),start=1):

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

    def _open_files(self,
                    files_list) -> bytearray:
        pass

    def create_initial_body_part(self, chat_id, boundary, filename):
        return (
            f"--{boundary}\r\n"
            f"Content-Disposition: form-data; name=\"chat_id\"\r\n\r\n"
            f"{chat_id}\r\n"
            f"--{boundary}\r\n"
            f"Content-Disposition: form-data; name=\"document\"; filename=\"{filename}\"\r\n"
            f"Content-Type: application/octet-stream\r\n\r\n"
        ).encode('utf-8')

    def create_final_body_part(self, boundary):
        return f"\r\n--{boundary}--\r\n".encode('utf-8')

    def send_file_to_telegram(self, chat_id, file_path, bot_token):
        boundary = '----WebKitFormBoundary' + str(uuid.uuid4()).replace('-', '')
        filename = file_path.split('/')[-1]

        initial_part = self.create_initial_body_part(chat_id,
                                                     boundary, filename)
        final_part = self.create_final_body_part(boundary)

        host = "api.telegram.org"
        method_url = f"/bot{bot_token}/sendDocument"
        headers = {
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        }

        # Open file in binary mode
        with open(file_path, "rb") as file:
            file_data = file.read()

        # Calculate content length
        content_length = len(initial_part) + len(file_data) + len(final_part)
        headers["Content-Length"] = str(content_length)

        # Open connection and send request
        connection = http.client.HTTPSConnection(host)
        connection.putrequest("POST", method_url)
        for header, value in headers.items():
            connection.putheader(header, value)
        connection.endheaders()

        # Stream the request parts
        connection.send(initial_part)
        connection.send(file_data)
        connection.send(final_part)

        # Get response
        response = connection.getresponse()
        print(response.status, response.reason)
        data = response.read()
        print(data)

        connection.close()


    bot_token = os.getenv("tg_lazy_bot")
    chat_id = os.getenv("chat_ing")
    file_path = 'examples/example.png'

    chat_ids = [chat_id, chat_id]  # List of chat IDs

    for chat_id in chat_ids:
        send_file_to_telegram(chat_id, file_path, bot_token)

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
    #         url = f"https://api.telegram.org/bot{self.api_key_value}/sendAudio"

    #     else:
    #         url = f"https://api.telegram.org/bot{self.api_key_value}/sendDocument"

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
