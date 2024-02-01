from . import Dispatcher
from logging import Handler, LogRecord

class TgLogger(Handler):
    def __init__(self, dispatcher: Dispatcher, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.dispatcher = dispatcher

    def emit(self, record: LogRecord) -> None:
        log_entry = self.format(record)
        self.dispatcher.send_message(log_entry)
