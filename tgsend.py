#!/usr/bin/env python3

"""

   If you dont want to install "requests" lib globally, you can modify shebang, and provide link to python in virtual environment

"""

# -------------------------------------------------------- imports --------------------------------------------------------- #

import os
import argparse
import json

import requests


# -------------------------------------------------------- classes --------------------------------------------------------- #


# donno how it works in other shells, so be careful about it, I dont dive a fuck

class ColorString:

    COLORS = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m"
        }

    END_COLOR = "\033[0m"

    def __init__(self, color="cyan", text="default string"):
        self.color = color
        self.text = text

    def __str__(self):
        color_code = self.COLORS.get(self.color, self.COLORS["cyan"])
        return f"{color_code}{self.text}{self.END_COLOR}"



# ----------------------------------------------------- default values ----------------------------------------------------- #

contacts_file_name = ".tgsend.contacts"

current_file_dir = os.path.dirname(os.path.realpath(__file__))

contacts_file_path = os.path.join(current_file_dir, contacts_file_name)

contacts_file_exists = os.path.exists(contacts_file_path)




# ------------------------------------------------------- functions -------------------------------------------------------- #

def message_handler(api_key = None, chat_id = None, messages = None, documents = None, audiofiles = None):

    """
    massage handler takes:

    api_key - telegram bot's API key

    chat_id - chat associated with the bot

    messages - list of messages
    ["message1", "message2"]

    documents - list of files' paths

    audiofiles - list of audiofiles' paths
    (the audiofile can be sent as a regular file, but the user will not be able to play it in a telegram then)

    """


    if (api_key == None) or (chat_id == None):
        print(ColorString(color = "red", text = "bot's API key and chat id are required"))
        return


    all_tries = (0 if messages is None else len(messages)) + (0 if documents is None else len(documents))  + (0 if audiofiles is None else len(audiofiles))

    if (all_tries == 0):
        print(ColorString(color = "red", text = "At least one argument for sending is required"))
        return


    sending_success = []

    sending_errors = []


    if messages is not None:

        m_url = f"https://api.telegram.org/bot{api_key}/sendMessage"

        for message in messages:

            params = {"chat_id": chat_id, "text": message}

            response = requests.post(m_url, data = params)

            if response.status_code == 200:
                sending_success.append(message)

            else: #I added try-except block here and in documents, couse mb future server response will be changed
                try:
                    description = ColorString(color = "red", text = json.loads(response.content)["description"])

                except (json.JSONDecodeError, KeyError):
                    description = response.content

                sending_errors.append(f"{message}:\n\t{description}")


    if documents is not None:

        d_url = f"https://api.telegram.org/bot{api_key}/sendDocument"

        for doc in documents:

            max_file_size = 50_000_000 #50 mb is max for 1 file telegram bots

            if  os.path.exists(doc) and os.path.getsize(doc) < max_file_size:

                response = requests.post(d_url, data = {"chat_id": chat_id}, files = {"document": open(doc, "rb")})

                if response.status_code == 200:
                    sending_success.append(doc)

                else:
                    try:
                        description = ColorString(color = "red", text = json.loads(response.content)["description"])
                    except (json.JSONDecodeError, KeyError):
                        description = response.content
                    sending_errors.append(f"{doc}:\n\t{description}")

            elif  os.path.exists(doc) and os.path.getsize(doc) > max_file_size:
                description = ColorString(color = "red", text = f"file is bigger than bot's file limit, skipped")
                sending_errors.append(f"{doc}:\n\t{description}")

            elif not os.path.exists(doc):
                description = ColorString(color = "red", text = f"file not found")
                sending_errors.append(f"{doc}:\n\t{description}")

            else:
                print(ColorString(color = "cian", text = f"some unexpected problem with file: \"{doc}\""))

    if audiofiles is not None:

        a_url = f"https://api.telegram.org/bot{api_key}/sendAudio"

        for audio in audiofiles:

            max_file_size = 50_000_000 #50 mb is max for 1 file telegram bots

            if  os.path.exists(audio) and os.path.getsize(audio) < max_file_size:

                response = requests.post(a_url, data = {"chat_id": chat_id}, files = {"audio": open(audio, "rb")})

                if response.status_code == 200:
                    sending_success.append(audio)

                else:
                    try:
                        description = ColorString(color = "red", text = json.loads(response.content)["description"])
                    except (json.JSONDecodeError, KeyError):
                        description = response.content
                    sending_errors.append(f"{audio}:\n\t{description}")

            elif  os.path.exists(audio) and os.path.getsize(audio) > max_file_size:
                description = ColorString(color = "red", text = f"file is bigger than bot's file limit, skipped")
                sending_errors.append(f"{audio}:\n\t{description}")

            elif not os.path.exists(audio):
                description = ColorString(color = "red", text = f"file not found")
                sending_errors.append(f"{audio}:\n\t{description}")

            else:
                print(ColorString(color = "cian", text = f"some unexpected problem with file \"{audio}\""))


    if (all_tries != 0) and (all_tries == len(sending_success)):
        print(ColorString(color = "green", text = "Sent successfully"))

    elif (all_tries > 0) and (len(sending_success) == 0):
        print(ColorString(color = "red", text = "Errors by sending all messages:"), *sending_errors, sep = "\n")

    elif (all_tries > 0)  and (len(sending_success) > 0):
        print(ColorString(color = "red", text = "Errors by sending some messages:"), *sending_errors, sep = "\n")
        print(ColorString(color = "green", text = "\nOther messages send:"), *sending_success)

    else:
        print(ColorString(color = "cian", text = f"some unexpected problem with errors counting"))



def contacts_creator(api_key = None):

    if not contacts_file_exists:

        file_structure = {"bot_api_key" : api_key,
                          "default_chat" : None,
                          "contacts": {}}

        with open(contacts_file_path, "w") as contacts:
            json.dump(file_structure, contacts)

        print(ColorString(color = "green", text = "contacts file created"))

    else:
        print(ColorString(color = "red", text = "file \".tgsend.contacts\" already exists"))


def contacts_show():

    if contacts_file_exists and (saved_contacts != None):
        for name in saved_contacts.keys():
            print(f"{name}: {saved_contacts[name]}")

    elif not contacts_file_exists:
        print(ColorString(color = "red", text = "contacts file not found"))

    elif contacts_file_exists and (saved_contacts == None):
        print(ColorString(color = "yellow", text = "contacts file is empty"))

    else:
        print(ColorString(color = "cian", text = f"some unexpected problem by showing contacts file"))


def contacts_editor(chat_add = None, chat_remove = None):

    print(ColorString(color = "magenta", text = "this function will be added in future update, but you can manually edit contacts file"))
    pass

    # if not contacts_file_exists:
    #     print(ColorString(color = "red", text = "contacts file not found"))

    # else:

    #     if chat_add != None:

    #         contact_name = chat_add[0]
    #         contact_number = chat_add[1]

    #         if (type(contact_name) != string) or (type(contact_number) != integer):
    #             print(ColorString(color = "red", text = "values must be string and integer"))


    #         if contact_name in saved_contacts.keys():
    #             print(ColorString(color = "red", text = "contact with this name already exists"))

    #         else:

    #         with open(contacts_file_path, "w") as contacts:

    #             elif chat_remove != None:

def get_id(api_key = None, searching_username = None, searching_text = None):

    if api_key != None:

        try:

            url = f'https://api.telegram.org/bot{api_key}/getUpdates'

            response = requests.get(url)

            if response.status_code == 200:

                data = json.loads(response.content)

                messages = data["result"]

                result = None

                if len(messages) == 0:

                    print(ColorString(color = "red", text = "no messages found"))
                    return

                if searching_username != None:

                    for message in messages:
                        if message["message"]["from"]["username"] == searching_username:
                            text = message["message"]["text"]
                            chat_id = message["message"]["chat"]["id"]
                            result = (searching_username, chta_id, text)
                            break

                elif searching_text != None:

                    for message in messages:
                        if message["message"]["text"] == searching_text:
                            username = message["message"]["from"]["username"]
                            chat_id = message["message"]["chat"]["id"]
                            result = (searching_username, chat_id, text)
                            break

                else:

                    result = []
                    for message in messages:
                        text = message["message"]["text"]
                        username = message["message"]["from"]["username"]
                        chat_id = message["message"]["chat"]["id"]
                        result.append(f"{searching_username} {chat_id} {text}")


                if result != None:
                    print(*result)

                else:
                    print(ColorString(color = "red", text = "nothing found"))

        except (json.JSONDecodeError, KeyError):
            print(ColorString(color = "red", text = "Some unexpected problem"))

    else:
        print(ColorString(color = "red", text = "API-key required"))

# ------------------------------------------------------- main part -------------------------------------------------------- #

def main():

    # try to read contacts file
    if contacts_file_exists:
        with open (contacts_file_path, "r") as contacts_file:
            try:
                data = json.load(contacts_file)
                bot_api_key = data["bot_api_key"]
                default_chat = data["default_chat"]
                saved_contacts = data["contacts"] if (len(data["contacts"]) != 0) else None
            except (json.JSONDecodeError, IndexError):
                print(ColorString(color = "yellow", text = "contacts file is corrupted"))

                bot_api_key = None
                default_chat = None
                saved_contacts = None

    else:
        bot_api_key = None

        default_chat = None

        saved_contacts = None

    # setup parser and subparser
    parser = argparse.ArgumentParser(description="Send message or/and document from shell to Telegram",
                                     epilog="https://github.com/signifex")

    subparsers = parser.add_subparsers(title="commands",
                                       description="valid commands",
                                       dest="command",
                                       help="description")


    # main parser for sending messages and documents
    message_handler_parser = subparsers.add_parser("send", help = "send message or file to chat")

    message_handler_parser.add_argument("-A", "--api_key",
                                        metavar = "<API-key>",
                                        dest = "sending_bot_api",
                                        default = bot_api_key,
                                        help = "bot's api key, by default will be readed from contacts file")

    recipient = message_handler_parser.add_mutually_exclusive_group(required = False)

    recipient.add_argument("-t", "--to_saved_chat",
                           metavar = "<chat name>",
                           dest = "sending_chat_name",
                           type = str,
                           help = "name from contacts list to send message")


    recipient.add_argument("-T", "--to_manual_chat",
                           metavar = "<chat id>",
                           dest = "sending_chat_id",
                           type = int,
                           default = default_chat,
                           help = "chat_id to send message")


    message_handler_parser.add_argument("-m", "--message",
                                        metavar = "message",
                                        dest = "sending_messages",
                                        nargs = "+",
                                        help = "send message(s) to chat")


    message_handler_parser.add_argument("-d", "--document",
                                        metavar = "file",
                                        dest = "sending_documents",
                                        nargs = "+",
                                        help = "send file(s) to chat")


    message_handler_parser.add_argument("-a", "--audio",
                                        metavar = "audiofile",
                                        dest = "sending_audiofiles",
                                        nargs = "+",
                                        help = "send audiofile(s) to chat")


    # parser for creating contacts file, API key is optional
    creation_file_parser = subparsers.add_parser("create", help = "create contacts file")

    creation_file_parser.add_argument("-A", "--api_key",
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

    editor.add_argument("-R", "--remove",
                        metavar = "<chat name>",
                        dest = "editor_remove",
                        help = "remove saved contacts")

    # parser to get updates - easy way to get own chat number

    get_id_parser = subparsers.add_parser("getid", help = "get updates from bot and return messages with chat id")

    get_id_parser.add_argument("-A", "--api_key",
                               metavar = "API-key",
                               dest = "get_id_api_key",
                               default = bot_api_key,
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

    if args.command == "create":
        contacts_creator(api_key = args.creation_api_key)

    elif args.command == "getid":
        get_id(api_key = args.get_id_api_key, searching_username = args.get_id_by_username, searching_text = args.get_id_by_text)

    elif args.command == "list":
        contacts_show()

    elif args.command == "contacts":
        contacts_editor(chat_add = args.editor_add, chat_remove = args.editor_remove)



    elif args.command == "send":

        extracted_chat_id = None

        if (args.sending_chat_id == None and args.sending_chat_name == None):
            print(ColorString(color = "red", text = f"missed chat name or chat id"))

        if args.sending_bot_api == None:
            print(ColorString(color = "red", text = f"missed bot's API"))

        if args.sending_chat_id != None:
            extracted_chat_id = args.sending_chat_id

        elif args.sending_chat_name != None and contacts_file_exists:

            try:
                extracted_chat_id = saved_contacts[args.sending_chat_name]

            except KeyError:
                print(ColorString(color = "red", text = f"contact \"{args.sending_chat_name}\" not found"))

        elif args.sending_chat_name != None and not contacts_file_exists:
            print(ColorString(color = "red", text = "contact file not found"))

        else:
            print(ColorString(color = "cian", text = "some unexpected problem with extracting arguments for send subcommand"))
            print(args)
            exit()

        message_handler(api_key = args.sending_bot_api, chat_id = extracted_chat_id, messages = args.sending_messages, documents = args.sending_documents, audiofiles = args.sending_audiofiles)



    else:
        print(ColorString(color = "yellow", text = 'No command specified. Use --help for more information.'))

    exit()

# -------------------------------------------------- lets start this shit -------------------------------------------------- #

if __name__ == "__main__":
    main()

# -------------------------------------------------------- old shit -------------------------------------------------------- #


# elif args.command == 'delete':
#     url = f'https://api.telegram.org/bot{api_key}/deleteMessage'
#     params = {
#         'chat_id': args.chat_id,
#         'message_id': args.message_id,
#     }
#     response = requests.post(url, data=params)
#     if response.status_code == 200:
#         print('Message deleted successfully')
#     else:
#         print(f'Error deleting message: {response.content}')


# # delete command
# delete_parser = subparsers.add_parser('delete', help='delete a message')
# delete_parser.add_argument('--chat_id', type=int, required=True, help='Chat ID')
# delete_parser.add_argument('--message_id',

# need to repair getid function, it returns nothing, if you call it like "tgsend getid -A "some unrealistic api"".

# mb re-write ColorString, but donno, probably its not a good idea, to ruin a good working class



