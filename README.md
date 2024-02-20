# `tgsend` Pre-build documentation

`tgsend.py`, is created to work with telegram bots, `sending messages`, `sending documents`, `bulk messaging` and `logging`. Also functions for storing api-keys and contacts.

## Features of this version:
- Independence from `any third-party installed libraries`. For sending messages, the script uses built-in `http.client` for making API-call requests.
- Memory-effective file sending: instead of re-opening the same files for each recipient, creates multiple parts of a request body to share the same open files between threads. 
- Different recipients groups: created object of the class `Dispatcher` will store API-key and group of recipients.
- `Async`: sending messages or files proceeding to all recipients at the same time, instead of one-by-one (helpful to avoid reopening the same files for each recipient).
- File Management: create a new contacts file, edit existing contacts, including adding or removing API keys, encrypt or decrypt the contacts file.
- Command-line interface with common arguments style. #need to create new
- Some basic file protection and file integrity check.


## Usage:

### 1. Command Line:

The script provides a command-line interface, allowing users to execute various operations directly from the terminal. The `Handler` class manages these command-line interactions.

To use the script from the command line, navigate to the directory containing `tgsend.py` and run:

```bash
python tgsend.py [command] [options]
```

Replace `[command]` with the desired operation (e.g., `send`, `create`, `edit`, etc.) and `[options]` with any additional parameters or flags required for that operation.

### 2. As an Imported Module:

You can also use `tgsend.py` as a module in your Python projects. Simply import the necessary classes or methods and utilize them as needed.

```python
from tgsend import ContactsFile, Dispatcher
# Use the functionalities as required in your script.
```
current usage in Python interpreter:

![image](https://github.com/signifex/telegram_sh/assets/97762325/6f868241-cd02-4bfc-ba6d-859286e36c5b)

as logger:

![image](https://github.com/signifex/telegram_sh/assets/97762325/f643da13-654f-41e2-92e4-3dadb7186b0a)
![image](https://github.com/signifex/telegram_sh/assets/97762325/4ff711ea-148e-4133-a91a-12e670de9840)

