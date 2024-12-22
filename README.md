# secret-hitler-game
A Discord bot to play the board game, Secret Hitler, in a text channel with friends.

## Getting Started

### Prerequisites

You need to have Python installed. You can download it from [here](https://www.python.org/downloads/).

### Installation

Install the required packages using pip:

```shell
pip install discord python-dotenv
```

### Set up environment file
create a file named `.env` and add the following keys:<br>
1. `ENV=` where values can be `_DEV` or `_PROD`<br>
2. `DISCORD_TOKEN_DEV=` value of your dev discord token<br>
3. `DISCORD_TOKEN_PROD=` value of your prod discord token<br>

## Running the bot
### Run the bot locally
```shell
py ./secrethitler.py
```

### Running on AWS

1. switch to the root user
```shell
sudo su
```
2. Run the bot in the background use nohup (recommended)
```shell
nohup python3 -u hogbot.py &
```
3. You can also run the bot directly using python3 (optional)
```shell
python3 hogbot.py
```
4. Check the log output
```shell
tail -f nohup.out
```
5. Check the running processes
```shell
ps aux | grep python3
```
6. To kill a process where `[PID]` is the process ID you can find from the output of step 5
```shell
kill [PID]
```

## Commands
```shell
!join
```
```shell
!leave
```
```shell
!lobby
```
```shell
!start
```
```shell
!nominate [name]
```
```shell
!vote [ja/nein]
```
```shell
!discard [cardNum]
```
```shell
!enact [cardNum]
```
```shell
!investigate [name]
```
```shell
!appoint [name]
```
```shell
!kill [name]
```
```shell
!veto [ja/nein]
```