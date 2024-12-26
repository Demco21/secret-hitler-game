import discord
import os
import logging
from logging.handlers import RotatingFileHandler
from discord.ext import commands
from dotenv import load_dotenv
import random
import asyncio
from unittest.mock import MagicMock, AsyncMock

# Load environment variables from .env file
load_dotenv()

# Environment variables
ENV_TOKEN_SUFFIX = os.getenv('ENV')
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN' + ENV_TOKEN_SUFFIX)
SECRET_HITLER_CHANNEL_ID = int(os.getenv('SECRET_HITLER_CHANNEL_ID'))
FASCIST_CARD_EMOJI_NAME = os.getenv('FASCIST_CARD_EMOJI_NAME')
LIBERAL_CARD_EMOJI_NAME = os.getenv('LIBERAL_CARD_EMOJI_NAME')
FASCIST_CARD_EMOJI_ID = int(os.getenv('FASCIST_CARD_EMOJI_ID'))
LIBERAL_CARD_EMOJI_ID = int(os.getenv('LIBERAL_CARD_EMOJI_ID'))

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(
    filename='secret_hitler.log',
    mode='a',
    maxBytes=5*1024*1024,  # 5 MB
    backupCount=2,         # Keep up to 2 backup files
    encoding='utf-8',
    delay=0
)
handler.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(name)s: %(message)s'))
logger.addHandler(handler)

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Game States
GAME_NOT_STARTED = 0
GAME_STARTING = 1
NOMINATE_CHANCELLOR = 2
ELECTION = 3
PRESIDENTIAL_LEGISLATION = 4
CHANCELLOR_LEGISLATION = 5
EXECUTIVE_INVESTIGATION = 6
EXECUTIVE_EXAMINATION = 7
EXECUTIVE_APPOINTMENT = 8
EXECUTIVE_KILL = 9
AGENDA_VETOED = 10

# Role definitions
LIBERAL = "Liberal"
FASCIST = "Fascist"
HITLER = "Hitler"

# Game Types
FIVE_SIX_PLAYER_GAME_MODE = 'fiveplayers'
SEVEN_EIGHT_PLAYER_GAME_MODE = 'sevenplayers'
NINE_TEN_PLAYER_GAME_MODE = 'nineplayers'

# Images
SECRET_HITLER_LOGO_IMG = './images/logo/secret_hitler_logo.jpg'
LIBERAL_PARTY_CARD_IMG = './images/cards/liberal_party_card.jpg'
FASCIST_PARTY_CARD_IMG = './images/cards/fascist_party_card.jpg'
HITLER_CARD_IMG = './images/cards/hitler_card.jpg'
HITLER_ASSASSINATED_IMG = './images/cards/hitler_assassinated_card.jpg'
HITLER_CHANCELLOR_IMG = './images/cards/hitler_chancellor_card.jpg'

# Game Variables
game_state = GAME_NOT_STARTED
players = []
assassinated = []
role_assignments = {}
votes = {}
liberal_policies = 0
fascist_policies = 0
policy_cards = []
discarded_policies = []
top_cards = []
failed_election_count = 0
previous_president = None
current_president = None
current_chancellor = None
game_mode = None
game_channel = None

@bot.event
async def on_ready():
    global game_channel
    print(f"Logged in as {bot.user}")
    game_channel = bot.get_channel(SECRET_HITLER_CHANNEL_ID)

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        logger.info(f"User **{ctx.author.name}** is not allowed to use this command. Please make sure you meet the requirements.")
    else:
        logger.error(f"Command {ctx.command} caused an error. {error}")

def is_player():
    """Checks if the user is a player."""
    async def predicate(ctx):
        if ctx.author not in players:
            await ctx.send("Only players who have joined the game can use this command.")
            return False
        return True
    return commands.check(predicate)

def is_game_channel(showResponse=True):
    """Checks if user is messaging the game channel."""
    global game_channel
    async def predicateResponse(ctx):
        if ctx.channel.id != SECRET_HITLER_CHANNEL_ID:
            await ctx.send(f"This is the wrong channel! Please use **{game_channel.name}**.")
            return False
        return True
    async def predicateNoResponse(ctx):
        if ctx.channel.id != SECRET_HITLER_CHANNEL_ID:
            return False
        return True
    if showResponse:
        return commands.check(predicateResponse)
    else:
        return commands.check(predicateNoResponse)

@bot.command()
@is_game_channel()
async def tester(ctx, cmd, arg1, arg2=None):
    """Testing utility for developers."""
    global players
    if ENV_TOKEN_SUFFIX == '_PROD':
        return
    _players = {
        '1': {'name': 'Player1', 'id': 1},
        '2': {'name': 'Player2', 'id': 2},
        '3': {'name': 'Player3', 'id': 3},
        '4': {'name': 'Player4', 'id': 4},
        '5': {'name': 'Player5', 'id': 5},
        '6': {'name': 'Player6', 'id': 6},
        '7': {'name': 'Player7', 'id': 7},
        '8': {'name': 'Player8', 'id': 8},
        '9': {'name': 'Player9', 'id': 9}
    }
    noArgCommands = {
        'join': join,
        'ready': ready,
        'start': start,
        'leave': leave,
        'lobby': lobby,
        'reset': reset,
    }
    argCommands = {
        'nominate': nominate,
        'vote': vote,
        'discard': discard,
        'enact': enact,
        'investigate': investigate,
        'appoint': appoint,
        'kill': kill,
        'veto': veto
    }
    if cmd == 'join':
        if arg1 in _players:
            mock_author = MagicMock()
            mock_author.send = AsyncMock()
            mock_author.name = _players[arg1]['name']
            mock_author.id = _players[arg1]['id']
            ctx.author = mock_author
        else:
            await ctx.send('Invalid test player. Must be 1-9.')
            return
    else:
        found = False
        for player in players:
            if int(player.id) == int(arg1):
                ctx.author = player
                found = True
        if not found:
            await ctx.send('Invalid test player.')
            return
    if cmd in noArgCommands:
        await noArgCommands[cmd](ctx)
    elif cmd in argCommands:
        await argCommands[cmd](ctx, arg2)
    else:
        await ctx.send('Invalid command.')


@bot.command()
@is_game_channel()
async def join(ctx):
    """Allows a player to join the game."""
    global game_state

    if game_state != GAME_NOT_STARTED:
        await game_channel.send("The game has already started. Please wait for the next round!")
        return

    if ctx.author in players:
        await game_channel.send("You are already in the game!")
    elif len(players) >= 10:
        await game_channel.send("The game is full. Only 5 to 10 players can join!")
    else:
        players.append(ctx.author)
        await game_channel.send(f"**{ctx.author.name}** has joined the game! ({len(players)}/10 players)")

@bot.command()
@is_player()
@is_game_channel()
async def leave(ctx):
    """Leave a lobby."""
    global players
    if game_state == GAME_NOT_STARTED:
        players.remove(ctx.author)
        message = (f"**{ctx.author.name}** has left the lobby. ({len(players)}/8 players)")
        await game_channel.send(message)
    else:
        await game_channel.send("Match is in progress.")

@bot.command()
@is_player()
@is_game_channel()
async def ready(ctx):
    """Ready to play the game if enough players have joined."""
    global role_assignments, policy_cards, game_state, current_president, players, game_mode

    if len(players) < 5:
        await game_channel.send(f"You need at least 5 players to start the game! ({len(players)}/10 players)")
        return

    if len(players) > 10:
        await game_channel.send(f"The game can only have a maximum of 8 players! ({len(players)}/10 players)")
        return
    
    if game_state != GAME_NOT_STARTED:
        await game_channel.send("The game has already started!")
        return
    
    if len(players) in [5,6]:
        game_mode = FIVE_SIX_PLAYER_GAME_MODE
    if len(players) in [7,8]:
        game_mode = SEVEN_EIGHT_PLAYER_GAME_MODE
    if len(players) in [9,10]:
        game_mode = NINE_TEN_PLAYER_GAME_MODE
    await game_channel.send(file=discord.File(SECRET_HITLER_LOGO_IMG))
    await game_channel.send(get_intro_screen())
    game_state = GAME_STARTING
    
@bot.command()
@is_player()
@is_game_channel()
async def start(ctx):
    """Starts the game after ready."""
    global role_assignments, policy_cards, game_state, current_president, players, game_mode

    if len(players) < 5:
        await game_channel.send(f"You need at least 5 players to start the game! ({len(players)}/10 players)")
        return

    if len(players) > 10:
        await game_channel.send(f"The game can only have a maximum of 8 players! ({len(players)}/10 players)")
        return
    
    if game_state == GAME_NOT_STARTED:
        await game_channel.send("You must type !ready first.")
        return

    if game_state != GAME_STARTING:
        await game_channel.send("The game has already started!")
        return

    num_players = len(players)
    num_fascists = {5: 1, 6: 1, 7: 2, 8: 2, 9:3, 10:3}[num_players]
    num_liberals = num_players - num_fascists - 1

    logger.info(f"Starting game with {num_players} players in {game_mode} mode.")

    # Assign roles randomly
    roles = [HITLER] + [FASCIST] * num_fascists + [LIBERAL] * num_liberals
    random.shuffle(roles)
    role_assignments = {player: role for player, role in zip(players, roles)}
    logger.info("Players: [%s]", ", ".join(f"{player.name} ({player.id}) ({role})" for player, role in role_assignments.items()))

    # Create the stack of policy cards
    policy_cards = [LIBERAL] * 6 + [FASCIST] * 11
    random.shuffle(policy_cards)

    # Randomly select a candidate
    candidate = random.choice(players)
    current_president = candidate
    messageAfter = (
        f"The game has started! There will be **{num_liberals} Liberals** and **{num_fascists} Fascists** with **1 Secret Hitler**."
        f"\nYour first Presidential Candidate has been randomly selected as **{candidate.name}**!"
        f"\n**{candidate.name}** you must **!nominate** a Chancellor then the group will **!vote**."
        )
    await print_game_dashboard(None, messageAfter)
    await send_roles_to_players()
    game_state = NOMINATE_CHANCELLOR

@bot.command()
@is_player()
@is_game_channel()
async def nominate(ctx, nomination: str):
    """Allows the President to choose a Chancellor."""
    global role_assignments, game_state, current_chancellor, current_president

    # Check if the game state is in the nomination phase
    if game_state != NOMINATE_CHANCELLOR:
        await game_channel.send("Nomination is not allowed at this moment.")
        return
    
    if ctx.author != current_president:
        await game_channel.send("Only the President can nominate the Chancellor.")
        return
    
    chancellor = get_player_by_name(nomination)
    if chancellor is None:
        await game_channel.send("Could not find that player, try again.")
        return

    if chancellor == current_president:
        await game_channel.send("You can't nominate yourself as Chancellor, pick someone else.")
        return
    
    if chancellor == previous_president:
        await game_channel.send("You can't nominate the most recent President as Chancellor, nominate a different Chancellor.")
        return
    
    current_chancellor = chancellor
    await game_channel.send(f"President **{current_president.name}** has nominated **{chancellor.name}** as Chancellor, time to cast your votes!\nEveryone cast your votes by typing **!vote ja** or **!vote nein**")
    game_state = ELECTION
    

@bot.command()
@is_player()
@is_game_channel()
async def vote(ctx, vote: str):
    """Allows players to vote Ja! or Nein! on the current candidate."""
    global role_assignments, game_state, failed_election_count, current_president, previous_president, current_chancellor, fascist_policies, policy_cards, top_cards, votes
    
    # Check if the game state is in the election phase
    if game_state != ELECTION:
        await game_channel.send("Voting is not allowed at this moment.")
        return
    
    if ctx.author == current_chancellor or ctx.author == current_president:
        await game_channel.send("Chancellor and President do not vote!")
        return    
    
    # Check if the player is eligible to vote (not already voted)
    if ctx.author in votes:
        await game_channel.send("You have already voted!")
        return

    # Validate the vote input
    if vote.lower() not in ['ja', 'ja!', 'nein', 'nein!']:
        await game_channel.send("Please vote with either 'Ja!' or 'Nein!'")
        return
    
    # Record the vote
    votes[ctx.author] = vote

    # Check if all players have voted
    votes_needed = len(players) - 2 # minus chancellor and president
    voted_players = len(votes)

    if voted_players != votes_needed:
        await game_channel.send(f"votes: ({voted_players}/{votes_needed})")
    if voted_players == votes_needed:
        # Tally votes
        ja_votes = sum(1 for vote in votes.values() if vote.lower() in ['ja', 'ja!'])
        nein_votes = votes_needed - ja_votes
        message = (f"- Ja!: {ja_votes} votes\n- Nein!: {nein_votes} votes")
        if ja_votes > nein_votes:
            await election_success(message)
        else:
            await election_failed(message)
        # Reset the votes for the next round
        votes = {}

async def election_success(message):
    global role_assignments, fascist_policies, previous_president, current_president, top_cards, game_state, policy_cards
    if role_assignments[current_chancellor] == HITLER and fascist_policies >= 3:
        message += "\n\n**GAME OVER, HITLER WAS ELECTED CHANCELLOR! FASCISTS WIN!**"
        await game_over(message, HITLER_CHANCELLOR_IMG)
        return
    top_cards = policy_cards[:min(3, len(policy_cards))]
    policy_cards = policy_cards[min(3, len(policy_cards)):]
    message += (
        f"\nThe election was successful! **{current_president.name}** is your **President** and **{current_chancellor.name}** is your **Chancellor**!"
        f"\nDrawing the top 3 policy cards and sending them to President **{current_president.name}** for review..."
        f"\nPresident **{current_president.name}** must **!discard** one policy before Chancellor **{current_chancellor.name}** will **!enact** one."
        )
    await print_game_dashboard(None, message)
    president_message = (
        "As President, you will select 1 of the top policies to be discarded before the Chancellor has a chance to enact one of the policies."
        "\nDiscard one card using **!discard 1** or **!discard 2** or **!discard 3** to select."
    )
    await send_top_cards_img(current_president, president_message)
    game_state = PRESIDENTIAL_LEGISLATION

async def election_failed(message):
    global current_chancellor, current_president, policy_cards, game_state, failed_election_count
    enact_top_policy_msg = ''
    failed_election_count += 1
    if failed_election_count == 3:
        top_policy = policy_cards[0]
        enact_top_policy()
        enact_top_policy_msg = f'\nThis is the 3rd failed election so the **{top_policy}** policy on the top of the draw pile has been enacted.'
        failed_election_count = 0
    current_president = get_next_president()
    message += (
        f"The election failed! The candidates were not elected. {enact_top_policy_msg}"
        f"\n**{current_president.name}** has been chosen as the new Presidential Candidate."
        f"\n**{current_president.name}** you must **!nominate** a Chancellor then the group will **!vote** again."
        )
    await print_game_dashboard(None, message)
    game_state = NOMINATE_CHANCELLOR

@bot.command()
@is_player()
@is_game_channel()
async def discard(ctx, card: str):
    """Allows President to discard a policy."""
    global top_cards, game_state, current_chancellor, current_president
    
    if game_state != PRESIDENTIAL_LEGISLATION:
        await game_channel.send("You cannot discard any policies at this time.")
        return
    
    if ctx.author != current_president:
        await game_channel.send("Only the president can discard a policy.")
        return
    
    if card != '1' and card != '2' and card != '3':
        await game_channel.send("Invalid card number.")
        return
    
    cardNum = int(card)
    
    if cardNum > len(top_cards):
        await game_channel.send("Invalid card number.")
        return
    
    discarded_policies.append(top_cards.pop(cardNum-1))
    await game_channel.send(f"Your President **{current_president.name}** has chosen a policy to **discard**.\nIt's time for your Chancellor **{current_chancellor.name}** to **!enact** a policy!")
    game_state = CHANCELLOR_LEGISLATION
    chancellor_message = (
        "As Chancellor, you will select one of the two policies left for you by the President to enact."
        "\nEnact one card using **!enact 1** or **!enact 2** to select"
    )
    await send_top_cards_img(current_chancellor, chancellor_message)

@bot.command()
@is_player()
@is_game_channel()
async def enact(ctx, card=None):
    """Allows Chancellor to enact a policy."""
    global top_cards, game_state, current_chancellor, current_president, previous_president, fascist_policies, liberal_policies
    
    if game_state != CHANCELLOR_LEGISLATION:
        await game_channel.send("You cannot enact any policies at this time.")
        return
    
    if ctx.author != current_chancellor:
        await game_channel.send("Only the Chancellor can enact a policy.")
        return
    
    if card not in {'1', '2'}:
        await game_channel.send("Invalid card number.")
        return

    cardNum = int(card)
    if cardNum > len(top_cards):
        await game_channel.send("Invalid card number.")
        return
    policy = get_enacted_policy_and_discard(cardNum)
    message = (
        f"Your Chancellor **{current_chancellor.name}** has chosen to enact a **{policy}** policy!"
    )

    if fascist_policies == 6:
        await game_channel.send(message)
        await game_over("**GAME OVER, 6 FASCIST POLICIES WERE ENACTED! FASCISTS WIN!**", get_fascist_board_img_file())
        return
    if liberal_policies == 5:
        await game_channel.send(message)
        await game_over("**GAME OVER, 5 LIBERAL POLICIES WERE ENACTED! LIBERALS WIN!**", get_liberal_board_img_file())
        return
    
    newGameState = NOMINATE_CHANCELLOR
    if policy == FASCIST:
        newGameState, message = process_presidential_powers(message)
    
    reshuffle_msg = start_new_round()
    if reshuffle_msg is not None:
        message += f"\n{reshuffle_msg}"

    if newGameState == EXECUTIVE_EXAMINATION:
        message += (
            f"\nSince 3 Fascist policies have been enacted, your President **{current_president.name}** gets to view the top 3 cards on the draw pile!"
        )
        await examine_top_cards()
        newGameState = NOMINATE_CHANCELLOR
    if newGameState == NOMINATE_CHANCELLOR:
        previous_president = current_president
        current_president = get_next_president()
        message += (
            f"\nIt's time for a new election! **{current_president.name}** will be nominated as new President!"
            f"\n**{current_president.name}** you must **!nominate** a Chancellor then the group will **!vote**."
        )
    await print_game_dashboard(None, message)
    game_state = newGameState

def get_enacted_policy_and_discard(cardNum):
    global top_cards, discarded_policies, fascist_policies, liberal_policies
    policy = top_cards.pop(cardNum-1)
    discarded_policies.extend(top_cards)
    top_cards = []
    if policy == FASCIST:
        fascist_policies += 1
    if policy == LIBERAL:
        liberal_policies += 1
    return policy

def process_presidential_powers(message):
    global fascist_policies, game_mode, current_president
    if (fascist_policies == 2 and game_mode == SEVEN_EIGHT_PLAYER_GAME_MODE) or (fascist_policies in [1,2] and game_mode == NINE_TEN_PLAYER_GAME_MODE):
        message += (
            f"\nSince 2 Fascist policies have been enacted, your President **{current_president.name}** gets to investigate one player's party membership!"
            f"\n**{current_president.name}** please choose a player to investigate using **!investigate [player_name]** (Ex. !investigate bob)"
            )
        return EXECUTIVE_INVESTIGATION, message
    elif fascist_policies == 3 and game_mode in [SEVEN_EIGHT_PLAYER_GAME_MODE, NINE_TEN_PLAYER_GAME_MODE]:
        message += (
            f"\nSince 3 Fascist policies have been enacted, your President **{current_president.name}** gets to appoint the next president!"
            f"\n**{current_president.name}** please choose a player to appoint to president using **!appoint [player_name]** (Ex. !appoint bob)"
            )
        return EXECUTIVE_APPOINTMENT, message
    elif fascist_policies == 3 and game_mode == FIVE_SIX_PLAYER_GAME_MODE:
        return EXECUTIVE_EXAMINATION, message
    elif fascist_policies == 4:
        message += (
            f"\nSince 4 Fascist policies have been enacted, your President **{current_president.name}** gets to assassinate another player!"
            f"\n**{current_president.name}** please choose a player to assassinate using **!kill [player_name]** (Ex. !kill bob)"
            )
        return EXECUTIVE_KILL, message
    elif fascist_policies == 5:
        message += (
            f"\nSince 5 Fascist policies have been enacted, your President **{current_president.name}** gets to assassinate another player and **!veto** power is unlocked!"
            f"\nWhen choosing a policy, the **Chancellor** may **!veto** the policy agenda. If the **President** agrees, no policy is enacted."
            f"\n**{current_president.name}** please choose a player to assassinate using **!kill [player_name]** (Ex. !kill bob)"
            )
        return EXECUTIVE_KILL, message
    else:
        return NOMINATE_CHANCELLOR, message

@bot.command()
@is_player()
@is_game_channel()
async def investigate(ctx, suspect_name: str):
    """Allows the President to investigate a party member."""
    global role_assignments, game_state, current_chancellor, current_president, previous_president, game_channel

    # Check if the game state is in the nomination phase
    if game_state != EXECUTIVE_INVESTIGATION:
        await game_channel.send("Investigation is not allowed at this moment.")
        return
    
    if ctx.author != current_president:
        await game_channel.send("Only the President can nominate the Chancellor.")
        return
    
    suspect = get_player_by_name(suspect_name)
    if suspect is None:
        await game_channel.send("Could not find that player, try again.")
        return
    
    await ctx.author.send(
        f"**{suspect.name}** is part of the **{role_assignments[suspect]}** party"
    )
    previous_president = current_president
    current_president = get_next_president()
    messageAfter = f"**{ctx.author.name}** has investigated which party **{suspect_name}** is truly loyal to."
    reshuffle_msg = start_new_round()
    if reshuffle_msg is not None:
        messageAfter += f"\n\n{reshuffle_msg}"
    messageAfter = (
        f"\n\n It's time for a new election! **{current_president.name}** will be nominated as new President!"
        f"\n**{current_president.name}** you must **!nominate** a Chancellor then the group will **!vote**."
    )
    await print_game_dashboard(None, messageAfter)
    game_state = NOMINATE_CHANCELLOR

@bot.command()
@is_player()
@is_game_channel()
async def appoint(ctx, appointed_name: str):
    """Allows the President to appoint a party member."""
    global game_state, current_president, previous_president, game_channel

    # Check if the game state is in the nomination phase
    if game_state != EXECUTIVE_APPOINTMENT:
        await game_channel.send("Appointment is not allowed at this moment.")
        return
    
    if ctx.author != current_president:
        await game_channel.send("Only the President can appoint the next president.")
        return
    
    appointed_president = get_player_by_name(appointed_name)
    if appointed_president is None:
        await game_channel.send("Could not find that player, try again.")
        return
  
    if appointed_president == current_president:
        await game_channel.send("You can't appoint yourself, choose somebody else.")
        return
    
    previous_president = current_president
    current_president = appointed_president
    messageAfter = f"**{previous_president.name}** has appointed **{appointed_president.name}** as the next president!"
    reshuffle_msg = start_new_round()
    if reshuffle_msg is not None:
        messageAfter += f"\n\n{reshuffle_msg}"
    messageAfter += (
        f"\n\n It's time for a new election! **{appointed_president.name}** will be nominated as new President!"
        f"\n**{appointed_president.name}** you must **!nominate** a Chancellor then the group will **!vote**."
    )
    await print_game_dashboard(None, messageAfter)
    game_state = NOMINATE_CHANCELLOR

@bot.command()
@is_player()
@is_game_channel()
async def kill(ctx, targetName: str):
    """Allows the President to kill a party member."""
    global game_state, current_president, previous_president, players, game_channel

    if game_state != EXECUTIVE_KILL:
        await game_channel.send("Killing is not allowed at this moment.")
        return
    
    if ctx.author != current_president:
        await game_channel.send("Only the President can kill.")
        return
    
    victim = get_player_by_name(targetName)
    if victim is None:
        await game_channel.send("Could not find that player, try again.")
        return
    
    players.remove(victim)
    assassinated.append(victim)
    if role_assignments[victim] == HITLER:
        await game_over("**GAME OVER, HITLER HAS BEEN ASSASSINATED! LIBERALS WIN!**", HITLER_ASSASSINATED_IMG)
        return
    messageAfter = f"**{victim.name}** has been assassinated in cold blood! Oh dear!"
    reshuffle_msg = start_new_round()
    if reshuffle_msg is not None:
        messageAfter += f"\n\n{reshuffle_msg}"
    previous_president = current_president
    current_president = get_next_president()
    messageAfter += (
        f"\nIt's time for a new election! **{current_president.name}** will be nominated as new President!"
        f"\n**{current_president.name}** you must **!nominate** a Chancellor then the group will **!vote**."
    )
    await print_game_dashboard(None, messageAfter)
    game_state = NOMINATE_CHANCELLOR

@bot.command()
@is_player()
@is_game_channel()
async def veto(ctx, decision: str=None):
    """Allows the Chancellor to veto a policy agenda."""
    global game_state, current_president, previous_president, players, top_cards

    if fascist_policies != 5:
        await game_channel.send("Veto power is not yet unlocked. You must enact 5 Fascist policies.")
        return
    if game_state != CHANCELLOR_LEGISLATION and game_state != AGENDA_VETOED:
        await game_channel.send("Veto is not allowed at this moment.")
        return
    if ctx.author != current_chancellor and game_state == CHANCELLOR_LEGISLATION:
        await game_channel.send(f"Only the Chancellor **{current_chancellor.name}** can call a veto.")
        return
    if ctx.author != current_president and game_state == AGENDA_VETOED:
        await game_channel.send(f"Waiting for veto confirmation from the president **{current_president.name}**.")
        return
    
    if ctx.author == current_chancellor and game_state == CHANCELLOR_LEGISLATION:
        await game_channel.send(f"The Chancellor **{current_chancellor.name}** has called a veto to this policy agenda!"
                       f"\nThe president **{current_president.name}** must either **!veto** **Ja!** or **Nein!** to accept or block the veto.")
        game_state = AGENDA_VETOED
        return
    
    if ctx.author == current_president and game_state == AGENDA_VETOED:
        if decision.lower() in ['ja', 'ja!']:
            discarded_policies.extend(top_cards)
            top_cards = []
            previous_president = current_president
            current_president = get_next_president()
            messageAfter = (
                f"The President **{current_president.name}** has voted in **favor** of a veto to this policy agenda!"
                f"\nThe policies will all be discarded and this will be considered an election failure."
                )
            reshuffle_msg = start_new_round()
            if reshuffle_msg is not None:
                messageAfter += f"\n\n{reshuffle_msg}"
            messageAfter += (
                f"\n\nIt's time for a new election! **{current_president.name}** will be nominated as new President!"
                f"\n**{current_president.name}** you must **!nominate** a Chancellor then the group will **!vote**."
            )
            await print_game_dashboard(None, messageAfter)
            game_state = NOMINATE_CHANCELLOR
        if decision.lower() in ['nein', 'nein!']:
            await game_channel.send(f"The President **{current_president.name}** has voted **against** a veto of this policy agenda!"
                        f"\nThe current chancellor **{current_chancellor.name}** must **!enact** a policy!.")
            game_state = CHANCELLOR_LEGISLATION
        return
    
@bot.command()
@is_game_channel()
async def lobby(ctx):
    """Displays the members in the lobby."""
    global players
    if game_state == GAME_NOT_STARTED:
        if players:
            message = (f"**Players waiting in lobby:**")
            for player in players:
                message += (f"\n- {player.name}")
        else:
            message = "No players are currently in the lobby."
        await game_channel.send(message)
    else:
        await game_channel.send("Match is in progress.")

@bot.command()
@is_player()
@is_game_channel()
async def reset(ctx):
    """Resets the game to allow a new round."""
    reset_game()
    await game_channel.send("The game has been reset. Players can now join a new round!")

def get_player_by_name(player_name):
    # Find the player with the given name
    for player in players:
        if player.name == player_name:
            return player
    return None  # Return None if no player with that name is found

def get_next_player(current_player):
    global players
    current_index = players.index(current_player)
    next_index = (current_index + 1) % len(players)
    return players[next_index]

def get_next_president():
    global current_chancellor
    current_chancellor = None
    next_president = get_next_player(current_president)
    if next_president == previous_president:
        next_president = get_next_player(next_president)
    return next_president

async def print_game_dashboard(msgBefore=None, msgAfter=None):
    global players, assassinated, liberal_policies, fascist_policies, previous_president, policy_cards, discarded_policies
    message = (f"**Players**")
    for player in players:
        message += f"\n- {player.name}"
        if player == current_president:
            message += " **(President)**"
        if player == current_chancellor:
            message += " **(Chancellor)**"
        if player == previous_president and (liberal_policies + fascist_policies) > 0:
            message += " (Previous President)"
    for player in assassinated:
        message += f"\n- {player.name} (Assassinated)"
    message += (
        f"\n\n**Policy Deck** <:{LIBERAL_CARD_EMOJI_NAME}:{LIBERAL_CARD_EMOJI_ID}><:{FASCIST_CARD_EMOJI_NAME}:{FASCIST_CARD_EMOJI_ID}>"
        f"\n- Draw Pile: {len(policy_cards)} Cards"
        f"\n- Discard Pile: {len(discarded_policies)}"
        )
    if msgBefore:
        await game_channel.send(msgBefore)
    await game_channel.send(message)
    tasks = [
        game_channel.send(file=discord.File(get_liberal_board_img_file())), 
        game_channel.send(file=discord.File(get_fascist_board_img_file()))
        ]
    await asyncio.gather(*tasks)
    if msgAfter:
        await game_channel.send("\n**Game Updates**\n" + msgAfter)

def get_intro_screen():
    message = (
        "\n\n**Overview**"
        "\n- Players are divided into Liberals and Fascists, with one Secret Hitler."
        "\n- Liberals: Outnumber Fascists but don't know which party anyone else is assigned to."
        "\n- Fascists: Know which party everyone is assigned to, work together to help Hitler, and sow chaos."
        "\n- Hitler: Is a Fascist but does not know who his fellow Fascists are and tries to remain hidden."
        "\n\n⚙️ **Gameplay** ⚙️"
        "\n**Presidential Election:**"
        "\n- Each round, the President-elect nominates a Chancellor."
        "\n- All other players vote \"Ja\" or \"Nein\" in favor or against the current election."
        "\n- If the election fails, the President-elect rotates to the next person and they select another Chancellor, along with another election."
        "\n- If the election fails 3 times, a policy is drawn from the draw deck and enacted."
        "\n- If the election succeeds, move to Legislative Session"
        "\n**Legislative Session:**"
        "\n- President privately draws 3 policies, discards 1, and passes 2 to the Chancellor."
        "\n- Chancellor discards 1 and enacts the remaining policy."
        "\n- The Policy Deck contains 11 Fascist policies and only 6 Liberal Policies."
        "\n**Powers & Conflict:**"
        "\n- After 3 Fascist policies enacted, Presidential powers unlock (e.g., policy peek, player investigation, or assassination)."
        "\n\n**Win Conditions**"
        "\n- Liberals: Enact 5 Liberal policies or assassinate Hitler."
        "\n- Fascists: Enact 6 Fascist policies or elect Hitler as Chancellor after 3 Fascist policies."
        "\n\n🤔 **Tips**"
        "\n- Liberals outnumber Fascists, so try to blend in as a Liberal."
        "\n- The Chancellor's party loyalty will be questioned if he enacts a Fascist policy, but remember, the President limits his policy options so he can always blame him!"
        "\n- The President's party loyalty may come into question by the Chancellor, but remember, there's only 6 Liberal policies, maybe you got unlucky!"
        "\n\n⏳ Ready? Type **!start** to begin the game!"
        "\n(You can always type **!help** for more details.)"
    )
    return message

async def send_roles_to_players():
    global role_assignments, players
    # Send roles to players
    for player, role in role_assignments.items():
        if role == LIBERAL:
            await player.send(file=discord.File(LIBERAL_PARTY_CARD_IMG))
        elif role == FASCIST:
            other_fascists = [p.name for p, r in role_assignments.items() if r == FASCIST and p.name != player.name]
            hitler = [p.name for p, r in role_assignments.items() if r == HITLER]
            await player.send(file=discord.File(FASCIST_PARTY_CARD_IMG))
            await player.send(f"Other Fascists: {', '.join(other_fascists)}\nHitler: {', '.join(hitler)}")
        elif role == HITLER:
            fascists = [p.name for p, r in role_assignments.items() if r == FASCIST]
            await player.send(file=discord.File(HITLER_CARD_IMG))
            if len(players) < 7:
                await player.send(f"Other Fascists: {', '.join(fascists)}")

def enact_top_policy():
    global policy_cards, fascist_policies, liberal_policies
    top_policy = policy_cards.pop(0)
    discarded_policies.append(top_policy)
    if top_policy == FASCIST:
        fascist_policies += 1
    else:
        liberal_policies += 1
    
async def examine_top_cards():
    global policy_cards
    card_img_file = './images/cards/top_cards'
    for card in policy_cards[:3]:
        if card == FASCIST:
            card_img_file += '_1'
        else:
            card_img_file += '_0'
    card_img_file += '.jpg'
    await current_president.send(file=discord.File(card_img_file))
    await current_president.send("As an executive power, you get to view the top 3 policies in the draw deck. Here they are!")

async def send_top_cards_img(player, msg):
    global top_cards
    card_img_file = './images/cards/top_cards'
    for card in top_cards:
        if card == FASCIST:
            card_img_file += '_1'
        else:
            card_img_file += '_0'
    card_img_file += '.jpg'
    await player.send(file=discord.File(card_img_file))
    await player.send(msg)

def start_new_round():
    global game_state, policy_cards, discarded_policies
    message = None
    if len(policy_cards) < 3 and len(discarded_policies) > 0:
        policy_cards.extend(discarded_policies)
        discarded_policies.clear()
        random.shuffle(policy_cards)
        message = (f"Ran out of policy cards. Adding back all discarded policies and shuffling the deck...")
    return message

def reset_game():
    global players, game_started, role_assignments, game_state, liberal_policies, fascist_policies, policy_cards, failed_election_count, previous_president, current_president, current_chancellor
    players = []
    game_started = False
    role_assignments = {}
    game_state = 0
    liberal_policies = 0
    fascist_policies = 0
    policy_cards = []
    failed_election_count = 0
    previous_president = None
    current_president = None
    current_chancellor = None

async def game_over(msg, img=None):
    global players, assassinated, role_assignments
    fascists = []
    liberals = []
    hitler = None
    
    # Add players from the role_assignments
    for player in players:
        if role_assignments[player] == FASCIST:
            fascists.append(player)
        if role_assignments[player] == LIBERAL:
            liberals.append(player)
        if role_assignments[player] == HITLER:
            hitler = player

    # Add players from the assassinated list
    for player in assassinated:
        if role_assignments[player] == FASCIST:
            fascists.append(player)
        if role_assignments[player] == LIBERAL:
            liberals.append(player)
        if role_assignments[player] == HITLER:
            hitler = player

    # Construct the message with the list of players in each role
    msg += f"\n\n**Hitler:**\n- {hitler.name} (Assassinated)" if hitler in assassinated else f"\n\n**Hitler:**\n- {hitler.name}"
    
    msg += f"\n\n**Fascists:**\n" + "\n".join(f"- {fascist.name} (Assassinated)" if fascist in assassinated else f"- {fascist.name}" for fascist in fascists)
    
    msg += f"\n\n**Liberals:**\n" + "\n".join(f"- {liberal.name} (Assassinated)" if liberal in assassinated else f"- {liberal.name}" for liberal in liberals)
    
    if img:
        await game_channel.send(file=discord.File(img))
    await game_channel.send(msg)
    reset_game()

def get_liberal_board_img_file():
    global liberal_policies, failed_election_count
    return f"./images/boards/liberal/liberal_board_{liberal_policies}_{failed_election_count}.jpg"

def get_fascist_board_img_file():
    global liberal_policies, game_mode
    return f"./images/boards/fascist/{game_mode}/fascist_board_{fascist_policies}.jpg"

# Run the bot
bot.run(DISCORD_TOKEN)
