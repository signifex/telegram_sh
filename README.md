# `tgsend` Pre-build documentation

`tgsend.py`, is created to work with telegram bots, `sending messages`, `sending documents`, `bulk messaging` and `logging`. Also functions for storing api-keys and contacts.

## Features of this version:
- Independence from third-party installed libraries. For sending messages, the script uses built-in `urllib` library. `requests` or `aiohttp` are required to send files only.
- Different recipients groups: created object of the class `Dispatcher` will store API-key and group of recipients.
- `Async`: sending messages or files proceeding to all recipients at the same time, instead of one-by-one (helpful to avoid reopening the same files for each recipient).
- File Management: create a new contacts file, edit existing contacts, including adding or removing API keys, encrypt or decrypt the contacts file.
- Command-line interface with common arguments style.
- Very basic file protection and file integrity check.


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

