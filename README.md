# telegram_sh

This is deep re-writed version of old script:



1) more commands, to configurate bot, send messages or/and documents

2) writed to work in shell, so can take arguments from output of other shell commands

3) or can be imported as python module

4) help (-h/--help) for each command and globally and in python help function


How to setup tgsend

1) git clone

2) make sure that you have requests lib installed globally, or modify shebang

3) chmod +x tgsend.py

4) create simbolic link to $PATH


5) get api-key from BotFather

6) tgsend create -A api-key

7) send any message to bot (to create chat)

8) get chat id using tgsend getid, store it in your environment (contacts file editor will be added, probably soon)

Now you can send using:
  tgsend send [-h] [-A <API-key>] (-T <chat id> | -t <chat name>) [-m message [message ...]] [-d file [file ...]] [-a audiofile [audiofile ...]
 

![Screenshot 2023-03-30 05 05 22](https://user-images.githubusercontent.com/97762325/228718569-cf91b04f-ae99-45cd-9c61-c9e33c87153c.png)

  
![Screenshot 2023-03-30 05 06 28](https://user-images.githubusercontent.com/97762325/228718469-0bbbc9db-1794-4380-ba59-a8f1bd94d08a.png)

