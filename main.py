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

3) SENDING ALREADY OPEN DOCUMENT

4) aiohttp supporting
'''


# ------------------------------------------------ imports ------------------------------------------------- #

import argparse
import sys
from typing import List, Literal, Union, Optional, NoReturn

from . import logger
from .utilities import ModuleBaseException
from .dispatcher import Dispatcher
from .contacts import ContactsCreate, ContactsAdd, ContactsEdit

try:
    from decorations import Colorize
    COLORIZE = True
except ImportError:
    COLORIZE = False


# ----------------------------------------------- constants ------------------------------------------------ #

EXIT_STATUS = Literal[0, 1]

# ------------------------------------------------ classes ------------------------------------------------- #


class Handler:

    '''
    Main class of this script with a couple of function:

    handler - wrapper for dispatcher, that also extracts values from contacts file,
    calls dispatcher with extracted values and deals with errors.

    Basicly, handler is good for for one-time calling of the script, from terminal or another script.

    Also it will be better for logging, couse Dispatcher.send returns dictionaries of
    sending good and bad messages or/and files (and control sum of packages for sure).
    '''

    class HandlerError(ModuleBaseException):
        def __init__(self, *args):
            super.__init__(*args, error_title = "Wrong arguments")


    @classmethod
    def dispatcher_wrapper(cls,
                           api_key: str = None,
                           api_key_name: str = None,
                           chat_id: int = None,
                           chat_name: str = None,
                           no_color: bool = False,
                           print_success: bool = True,
                           message: str = None,
                           documents: List[str] = [],
                           audiofiles: List[str] = []
                           ) -> EXIT_STATUS:

        try:

            if (api_key and api_key_name) or (not api_key and not api_key_name):
                error = "saved API-key name (using -A flag for non-defualt values) OR manually provided API-key (using -M flag) required"
                raise cls.HandlerError(error)

            elif (chat_id and chat_name) or (not chat_id and not chat_name):
                error = "chat id name (from contacts file, using -t flag for non-default values) OR manually provided (using -T flag) required"
                raise cls.HandlerError(error)

            elif not any((messages, documents, audiofiles)):
                error = "nothing to send"
                raise cls.HandlerError(error)

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

        except ModuleBaseException as e:

            exit_status = 1

            if no_color:
                print(e)
                logging.error(e.log)

            else:
               error = Colorize(text = e.name, color = "red")
               print(error + ": " + e.message)

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

