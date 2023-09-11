import urllib.request
import urllib.parse
import asyncio

from io import BytesIO
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

from tgsend import logger
from tgsend.utilities import ModuleBaseException, Checkers, key_timestamp
from tgsend.contacts import SendingConfigs


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


    class DispatcherError(ModuleBaseException):
        pass


    def __init__(self, configs: SendingConfigs) -> NoReturn:

        self._api_key: str = configs.api_key
        self.api_key_name: str = configs.api_key_name
        self._recipients: Dict[int, str] = configs.recipients.copy()

        self._sending_success = {}
        self._sending_errors = {}

        self._invalid_packets = {}

        Utilities.Checkers.check_api_key(self.api_key)


    def _get_api_key(self):
        return self._api_key, self._api_key_name

    api_key = property(_get_api_key)


    def _get_recipients(self):
        return self._recipients

    recipients = property(_get_recipients)


    async def _message_handler(self, message) -> NoReturn:

        tasks = [self._message_dispatcher(messages, recipient_id, recipient_name) for recipient_id, recipient_name in self._recipients.items()]

        await asyncio.gather(*tasks)


    async def _message_dispatcher(self, messages: str, recipient_id: int, recipient_name: str) -> NoReturn:

        url = f"https://api.telegram.org/bot{self.api_key}/sendMessage"

        params = {"chat_id": recipient_id, "text": message}

        data = urllib.parse.urlencode(params).encode("utf-8")

        with await urllib.request.urlopen(url, data) as response:
            response_data = response.read().decode("utf-8")
            response_json = json.loads(response_data)

        key = Utilities.key_timestamp()

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

        key = Utilities.key_timestamp()

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

        if not REQUESTS and not AIOHTTP:
            raise ImportError("Files can't be send without 'requests' library")

        self._sending_success.clear()
        self._sending_errors.clear()

        Utilities.Checkers.check_files(packets = packets)

        checksum = len(self.recipients) * len(packet)

        asyncio.run(self._file_handler(packets = packets, p_type = "files"))

        return SendingStatus(success = self._sending_success, fail = self._sending_errors, checksum = checksum)


    def send_audiofiles(self, packets: List[str]) -> SendingStatus:

        if not REQUESTS:
            raise ImportError("Files can't be send without 'requests' library")

        Utilities.Checkers.check_audiofiles(packets = packets)

        self._sending_success.clear()
        self._sending_errors.clear()

        checksum = len(self.recipients) * len(packets)

        asyncio.run(self._file_handler(packets = packets, p_type = "audiofiles"))

        return SendingStatus(success = self._sending_success, fail = self._sending_errors, checksum = checksum)

