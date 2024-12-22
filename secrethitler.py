import discord
import os
import logging
from logging.handlers import RotatingFileHandler
from discord.ext import commands
from dotenv import load_dotenv
import random

# Load environment variables from .env file
load_dotenv()

# Environment variables
ENV_TOKEN_SUFFIX = os.getenv('ENV')
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN' + ENV_TOKEN_SUFFIX)
AFK_CHANNEL_ID = int(os.getenv('AFK_CHANNEL_ID'))
HOGBOT_CHANNEL_ID = int(os.getenv('HOGBOT_CHANNEL_ID'))
HOGBOT_USER_ID = int(os.getenv('HOGBOT_USER_ID'))
CHANCELLOR_ROLE_ID = int(os.getenv('CHANCELLOR_ROLE_ID'))
HOGBOT_SERVER_ID = int(os.getenv('HOGBOT_SERVER_ID'))

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

# Game variables
players = []
assassinated = []
roles = []
role_assignments = {}
game_state = 0
liberal_policies = 0
fascist_policies = 0
policy_cards = []
top_cards = []
discarded_policies = []
failed_election_count = 0
previous_president = None
current_president = None
current_chancellor = None

# Role definitions
LIBERAL = "Liberal"
FASCIST = "Fascist"
HITLER = "Hitler"

# States
GAME_NOT_STARTED = 0
NOMINATE_CHANCELLOR = 1
ELECTION = 2
PRESIDENTIAL_LEGISLATION = 3
CHANCELLOR_LEGISLATION = 4
EXECUTIVE_INVESTIGATION = 5
EXECUTIVE_APPOINTMENT = 6
EXECUTIVE_KILL = 7
AGENDA_VETOED = 8

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CheckFailure):
        logger.info(f"User {ctx.author.name} is not allowed to use this command. Please make sure you meet the requirements.")
    else:
        raise error

def is_player():
    """Checks if the user is a player."""
    async def predicate(ctx):
        if ctx.author not in players:
            await ctx.send("Only players who have joined the game can use this command.")
            return False
        return True
    return commands.check(predicate)

@bot.command()
async def join(ctx):
    """Allows a player to join the game."""
    global game_state

    if game_state != GAME_NOT_STARTED:
        await ctx.send("The game has already started. Please wait for the next round!")
        return

    if ctx.author in players:
        await ctx.send("You are already in the game!")
    elif len(players) >= 8:
        await ctx.send("The game is full. Only 5 to 8 players can join!")
    else:
        players.append(ctx.author)
        await ctx.send(f"{ctx.author.name} has joined the game! ({len(players)}/8 players)")

@bot.command()
@is_player()
async def leave(ctx):
    """Leave a lobby."""
    global players
    if game_state == GAME_NOT_STARTED:
        players.remove(ctx.author)
        message = (f"**{ctx.author.name}** has left the lobby. ({len(players)}/8 players)")
        await ctx.send(message)
    else:
        await ctx.send("Match is in progress.")

@bot.command()
@is_player()
async def start(ctx):
    """Starts the game if enough players have joined."""
    global roles, role_assignments, policy_cards, game_state, current_president, players

    if len(players) < 5:
        await ctx.send(f"You need at least 5 players to start the game! ({len(players)}/8 players)")
        return

    if len(players) > 8:
        await ctx.send(f"The game can only have a maximum of 8 players! ({len(players)}/8 players)")
        return
    
    if game_state != GAME_NOT_STARTED:
        await ctx.send("The game has already started!")
        return

    await ctx.send("The game has started! Assigning roles...")

    # Assign roles
    num_players = len(players)
    num_fascists = {5: 1, 6: 1, 7: 2, 8: 2}[num_players]
    num_liberals = num_players - num_fascists - 1

    roles = [HITLER] + [FASCIST] * num_fascists + [LIBERAL] * num_liberals
    random.shuffle(roles)
    
    logger.info(f"players: {players}")
    role_assignments = {
        player: {
            "role": role,
            "vote": None
        }
        for player, role in zip(players, roles)
    }

    logger.info(f"Role Assignments: {role_assignments}")

    # Send roles to players
    for player, details in role_assignments.items():
        role = details['role']
        if role == LIBERAL:
            await player.send(f"Your role is: {role}")
        elif role == FASCIST:
            other_fascists = [p.name for p,v in role_assignments.items() if v['role'] == FASCIST and p.name != player.name]
            hitler = [p.name for p,v in role_assignments.items() if v['role'] == HITLER]
            await player.send(f"Your role is: {role}\nOther Fascists: {', '.join(other_fascists)}\nHitler: {hitler}")
        elif role == HITLER:
            fascists = [p.name for p,v in role_assignments.items() if v['role'] == FASCIST]
            if num_players < 7:
                await player.send(f"Your role is: {role}\nOther Fascists: {', '.join(fascists)}")
            else:
                await player.send(f"Your role is: {role}")

    # Create the stack of policy cards
    policy_cards = [LIBERAL] * 6 + [FASCIST] * 11
    random.shuffle(policy_cards)

    # Randomly select a candidate
    candidate = random.choice(list(role_assignments.keys()))
    current_president = candidate
    game_state = NOMINATE_CHANCELLOR
    message = (
        "\nRoles have been assigned. Check your DMs for your role!"
        f"\n\n**Game Details:**"
        f"\n- Fascists: {num_fascists}"
        f"\n- Liberals: {num_liberals}"
        "\n- One of you is Hitler!"
        f"\n\n{get_game_dashboard()}"
        "\n\n**Liberal Win Conditions:**"
        "\n- Enact all 5 Liberal policies and you win!"
        "\n- OR assassinate Hitler and you win!"
        "\n**Fascist Win Conditions:**"
        "\n- Enact all 6 Fascist policies and you win!"
        "\n- OR if you elect Hitler as Chancellor after 3 or more Fascist policies have been enacted, you win!"
        f"\n\nYour first Presidential Candidate has been randomly selected as **{candidate.name}**!"
        f"\n**{candidate.name}** you must nominate a Chancellor and the group will vote, **Ja!** or **Nein!**.")
    await ctx.send(message)

@bot.command()
@is_player()
async def nominate(ctx, nomination: str):
    """Allows the President to choose a Chancellor."""
    global role_assignments, game_state, current_chancellor, current_president

    # Check if the game state is in the nomination phase
    if game_state != NOMINATE_CHANCELLOR:
        await ctx.send("Nomination is not allowed at this moment.")
        return
    
    if ctx.author != current_president:
        await ctx.send("Only the President can nominate the Chancellor.")
        return
    
    chancellor = get_player_by_name(nomination)
    if chancellor is None:
        await ctx.send("Could not find that player, try again.")
        return
    
    if chancellor == previous_president:
        await ctx.send("You can't nominate the most recent President as Chancellor, nominate a different Chancellor.")
        return
    
    current_chancellor = chancellor
    await ctx.send(f"President {current_president.name} has nominated {chancellor.name} as Chancellor, time to cast your votes!")
    game_state = ELECTION
    

@bot.command()
@is_player()
async def vote(ctx, vote: str):
    """Allows players to vote Ja! or Nein! on the current candidate."""
    global role_assignments, game_state, failed_election_count, current_president, previous_president, current_chancellor, fascist_policies, policy_cards, top_cards
    
    # Check if the game state is in the election phase
    if game_state != ELECTION:
        await ctx.send("Voting is not allowed at this moment.")
        return
    
    # Check if the player is eligible to vote (not already voted)
    if role_assignments[ctx.author]['vote']:
        await ctx.send("You have already voted!")
        return
    
    vote_options = ['ja', 'ja!', 'nein', 'nein!']

    # Validate the vote input
    if vote.lower() not in vote_options:
        await ctx.send("Please vote with either 'Ja!' or 'Nein!'")
        return
    
    # Record the vote
    role_assignments[ctx.author]['vote'] = vote.lower()

    # Check if all players have voted
    total_players = len(players)
    voted_players = sum(1 for player in players if 'vote' in role_assignments[player])
    await ctx.send(f"votes: ({voted_players}/{total_players})")

    if voted_players == total_players:
        # Tally votes
        ja_votes = sum(1 for player in players if role_assignments[player]['vote'].lower() in [vote_options[0], vote_options[1]])
        nein_votes = total_players - ja_votes  # All other votes are Nein

        # Display the results
        await ctx.send(f"\n\n**Election Results:**\n- Ja!: {ja_votes} votes\n- Nein!: {nein_votes} votes")

        # Determine the outcome
        if ja_votes > nein_votes:
            if role_assignments[current_chancellor]['role'] == HITLER and fascist_policies >= 3:
                await game_over(ctx, "**GAME OVER, HITLER WAS ELECTED CHANCELLOR! FASCISTS WIN!**")
                return
            message = (
                "The election was successful! The candidate is elected!"
                f"\n\n{get_game_dashboard()}"
                f"\n\nWaiting for your new President **{current_president.name}** to discard one policy before your Chancellor **{current_chancellor.name}** will implement one."
                )
            previous_president = current_president
            game_state = PRESIDENTIAL_LEGISLATION
            top_cards = policy_cards[:min(3, len(policy_cards))]
            policy_cards = policy_cards[min(3, len(policy_cards)):]
            president_message = (
                "As president, you will select 1 of the top policies to be discarded before the Chancellor has a chance to implement one of the policies."
                "\n\n**Policies:**"
            )
            for i, card in enumerate(top_cards, start=1):
                president_message += f"\nCard {i}: {card}"
            president_message += (
                "\n\nDiscard one card using the command **!discard [cardNumber]** (Ex. !discard 1)"
                "\nChoose wisely!"
            )
            await ctx.send(message)
            await current_president.send(president_message)

        else:
            failed_election_count += 1
            if failed_election_count == 4:
                # draw top policy card and implement it
                return
            next_player = get_next_player(current_president)
            if next_player == previous_president:
                next_player = get_next_player(next_player)
            current_chancellor = None
            current_president = next_player
            game_state = NOMINATE_CHANCELLOR
            await ctx.send(
                "The election failed! The candidate was not elected."
                f"\n\n{get_game_dashboard()}"
                f"\n**{current_president.name}** has been chosen as the new Presidential Candidate."
                f"\n**{current_president.name}** you must nominate a Chancellor and the group will vote, **Ja!** or **Nein!**."
                )
        # Reset the votes for the next round
        for player in role_assignments:
            role_assignments[player]['vote'] = None

@bot.command()
@is_player()
async def discard(ctx, card: str):
    """Allows President to discard a policy."""
    global top_cards, game_state, current_chancellor, current_president
    
    if game_state != PRESIDENTIAL_LEGISLATION:
        await ctx.send("You cannot discard any policies at this time.")
        return
    
    if ctx.author != current_president:
        await ctx.send("Only the president can discard a policy.")
        return
    
    if card != '1' and card != '2' and card != '3':
        await ctx.send("Invalid card number.")
        return
    
    cardNum = int(card)
    
    if cardNum > len(top_cards):
        await ctx.send("Invalid card number.")
        return
    
    discarded_policies.append(top_cards.pop(cardNum-1))
    game_state = CHANCELLOR_LEGISLATION
    await ctx.send(f"Your President {current_president.name} has chosen a policy to discard, it's time for your Chancellor {current_chancellor.name} to enact a policy!")
    
    chancellor_message = (
        "As chancellor, you will select one of the two policies left for you by the President to enact."
        "\n\n**Policies:**"
    )
    for i, card in enumerate(top_cards, start=1):
        chancellor_message += f"\nCard {i}: {card}"
    chancellor_message += (
        "\n\nEnact one card using the command **!enact [cardNumber]** (Ex. !enact 1)"
        "\nChoose wisely!"
    )
    await current_chancellor.send(chancellor_message)

@bot.command()
@is_player()
async def enact(ctx, card: str):
    """Allows Chancellor to enact a policy."""
    global top_cards, game_state, current_chancellor, current_president, previous_president, fascist_policies, liberal_policies
    
    if game_state != CHANCELLOR_LEGISLATION:
        await ctx.send("You cannot enact any policies at this time.")
        return
    
    if ctx.author != current_president:
        await ctx.send("Only the chancellor can enact a policy.")
        return
    
    if card != '1' and card != '2':
        await ctx.send("Invalid card number.")
        return
    
    cardNum = int(card)
    
    if cardNum > len(top_cards):
        await ctx.send("Invalid card number.")
        return
    
    policy = top_cards.pop(cardNum-1)
    discarded_policies.extend(top_cards)
    top_cards = []
    if policy == FASCIST:
        fascist_policies += 1
    if policy == LIBERAL:
        liberal_policies += 1

    message = (
        f"Your Chancellor **{current_chancellor.name}** has chosen to enact a {policy} policy!"
    )
    if policy == FASCIST and fascist_policies == 2:
        game_state = EXECUTIVE_INVESTIGATION
        message += (
            f"\n\nSince 2 Fascist policies have been enacted, your President **{current_president.name}** gets to investigate one player's party membership!"
            f"\n\n**{current_president.name}** please choose a player to investigate using **!investigate [player_name]** (Ex. !investigate bob)"
            )
        await ctx.send(message)
        return
    if policy == FASCIST and fascist_policies == 3:
        game_state = EXECUTIVE_APPOINTMENT
        message += (
            f"\n\nSince 3 Fascist policies have been enacted, your President **{current_president.name}** gets to appoint the next president!"
            f"\n\n**{current_president.name}** please choose a player to appoint to president using **!appoint [player_name]** (Ex. !appoint bob)"
            )
        await ctx.send(message)
        return
    if policy == FASCIST and fascist_policies == 4:
        game_state = EXECUTIVE_KILL
        message += (
            f"\n\nSince 4 Fascist policies have been enacted, your President **{current_president.name}** gets to assassinate another player!"
            f"\n\n**{current_president.name}** please choose a player to assassinate using **!kill [player_name]** (Ex. !kill bob)"
            )
        await ctx.send(message)
        return
    if policy == FASCIST and fascist_policies == 5:
        game_state = EXECUTIVE_KILL
        message += (
            f"\n\nSince 5 Fascist policies have been enacted, your President **{current_president.name}** gets to assassinate another player!"
            f"\n\n**{current_president.name}** please choose a player to assassinate using **!kill [player_name]** (Ex. !kill bob)"
            f"\n\nAdditionally, the **veto** power is now unlocked. The Chancellor may veto any policy agenda using **!veto** while deciding on a policy to enact."
            f"\nIf the President approves this veto (**!veto ja**), all policies will be discarded and the round will move on. This will be considered an inactive government."
            f"\nIf the President does not approve (**!veto nein**), the Chancellor will be forced to enact a policy."
            )
        await ctx.send(message)
        return
    if fascist_policies == 6:
        await ctx.send(message)
        await game_over(ctx, "**GAME OVER, 6 FASCIST POLICIES WERE ENACTED! FASCISTS WIN!**")
        return
    if liberal_policies == 5:
        await ctx.send(message)
        await game_over(ctx, "**GAME OVER, 5 LIBERAL POLICIES WERE ENACTED! LIBERALS WIN!**")
        return
    
    next_president = get_next_player(current_president)
    if next_president == previous_president:
        next_president = get_next_player(next_president)
    previous_president = current_president
    current_president = next_president
    reshuffle_msg = start_new_round()
    if reshuffle_msg is not None:
        message += f"\n\n{reshuffle_msg}"
    message += (
        f"\n\n{get_game_dashboard()}"
        f"\n\nIt's time for a new election! **{next_president.name}** will be nominated as new President!"
        f"\n**{next_president.name}** you must nominate a Chancellor and the group will vote, **Ja!** or **Nein!**."
    )
    await ctx.send(message)

@bot.command()
@is_player()
async def investigate(ctx, suspect_name: str):
    """Allows the President to investigate a party member."""
    global role_assignments, game_state, current_chancellor, current_president, previous_president

    # Check if the game state is in the nomination phase
    if game_state != EXECUTIVE_INVESTIGATION:
        await ctx.send("Investigation is not allowed at this moment.")
        return
    
    if ctx.author != current_president:
        await ctx.send("Only the President can nominate the Chancellor.")
        return
    
    suspect = get_player_by_name(suspect_name)
    if suspect is None:
        await ctx.send("Could not find that player, try again.")
        return
    
    await ctx.author.send(
        f"{suspect.name} is part of the {role_assignments[suspect]['role']} party"
    )
    next_president = get_next_player(current_president)
    if next_president == previous_president:
        next_president = get_next_player(next_president)
    previous_president = current_president
    current_president = next_president
    message = f"{ctx.author.name} has investigated which party {suspect_name} is truly loyal to."
    reshuffle_msg = start_new_round()
    if reshuffle_msg is not None:
        message += f"\n\n{reshuffle_msg}"
    message += (
        f"\n\n{get_game_dashboard()}"
        f"\n\n It's time for a new election! **{next_president.name}** will be nominated as new President!"
        f"\n**{next_president.name}** you must nominate a Chancellor and the group will vote, **Ja!** or **Nein!**."
    )
    await ctx.send(message)
    
@bot.command()
@is_player()
async def appoint(ctx, appointed_name: str):
    """Allows the President to appoint a party member."""
    global game_state, current_president, previous_president

    # Check if the game state is in the nomination phase
    if game_state != EXECUTIVE_APPOINTMENT:
        await ctx.send("Appointment is not allowed at this moment.")
        return
    
    if ctx.author != current_president:
        await ctx.send("Only the President can appoint the next president.")
        return
    
    appointed_president = get_player_by_name(appointed_name)
    if appointed_president is None:
        await ctx.send("Could not find that player, try again.")
        return
    
    if appointed_president == current_president:
        await ctx.send("You can't appoint yourself, choose somebody else.")
        return
    
    previous_president = current_president
    current_president = appointed_president
    message = f"**{previous_president.name}** has appointed **{appointed_president.name}** as the next president!"
    reshuffle_msg = start_new_round()
    if reshuffle_msg is not None:
        message += f"\n\n{reshuffle_msg}"
    message += (
        f"\n\n{get_game_dashboard()}"
        f"\n\n It's time for a new election! **{appointed_president.name}** will be nominated as new President!"
        f"\n**{appointed_president.name}** you must nominate a Chancellor and the group will vote, **Ja!** or **Nein!**."
    )
    await ctx.send(message)

@bot.command()
@is_player()
async def kill(ctx, targetName: str):
    """Allows the President to kill a party member."""
    global game_state, current_president, previous_president, players

    if game_state != EXECUTIVE_KILL:
        await ctx.send("Killing is not allowed at this moment.")
        return
    
    if ctx.author != current_president:
        await ctx.send("Only the President can kill.")
        return
    
    victim = get_player_by_name(targetName)
    if victim is None:
        await ctx.send("Could not find that player, try again.")
        return
    
    if role_assignments[victim]['role'] == HITLER:
        await game_over(ctx, "**GAME OVER, HITLER HAS BEEN ASSASSINATED! LIBERALS WIN!**")
        return
    
    next_president = get_next_player(current_president)
    if next_president == previous_president:
        next_president = get_next_player(next_president)
    previous_president = current_president
    current_president = next_president
    players.remove(victim)
    assassinated.append(victim)
    message = f"**{victim.name}** has been assassinated in cold blood! Oh dear!"
    reshuffle_msg = start_new_round()
    if reshuffle_msg is not None:
        message += f"\n\n{reshuffle_msg}"
    message += (
        f"\n\n{get_game_dashboard()}"
        f"\n\n It's time for a new election! **{next_president.name}** will be nominated as new President!"
        f"\n**{next_president.name}** you must nominate a Chancellor and the group will vote, **Ja!** or **Nein!**."
    )
    await ctx.send(message)

@bot.command()
@is_player()
async def veto(ctx, decision: str=None):
    """Allows the Chancellor to veto a policy agenda."""
    global game_state, current_president, previous_president, players, top_cards

    if fascist_policies != 5:
        await ctx.send("Veto power is not yet unlocked. You must enact 5 Fascist policies.")
        return
    if game_state != CHANCELLOR_LEGISLATION and game_state != AGENDA_VETOED:
        await ctx.send("Veto is not allowed at this moment.")
        return
    if ctx.author != current_chancellor and game_state == CHANCELLOR_LEGISLATION:
        await ctx.send(f"Only the Chancellor **{current_chancellor.name}** can call a veto.")
        return
    if ctx.author != current_president and game_state == AGENDA_VETOED:
        await ctx.send(f"Waiting for veto confirmation from the president **{current_president.name}**.")
        return
    
    if ctx.author == current_chancellor and game_state == CHANCELLOR_LEGISLATION:
        await ctx.send(f"The Chancellor **{current_chancellor.name}** has called a veto to this policy agenda!"
                       f"\nThe president **{current_president.name}** must either vote **Ja!** or **Nein!** to this veto using command **!veto [decision]** (Ex. !veto ja)")
        game_state = AGENDA_VETOED
        return
    
    if ctx.author == current_president and game_state == AGENDA_VETOED:
        if decision.lower() in ['ja', 'ja!']:
            discarded_policies.extend(top_cards)
            top_cards = []
            next_president = get_next_player(current_president)
            if next_president == previous_president:
                next_president = get_next_player(next_president)
            previous_president = current_president
            current_president = next_president
            message = (
                f"The President **{current_president.name}** has agreed to a veto to this policy agenda!"
                f"\nThe policies will all be discarded and this will be considered as a time of inactive government."
                )
            reshuffle_msg = start_new_round()
            if reshuffle_msg is not None:
                message += f"\n\n{reshuffle_msg}"
            message += (
                f"\n\n{get_game_dashboard()}"
                f"\n\nIt's time for a new election! **{next_president.name}** will be nominated as new President!"
                f"\n**{next_president.name}** you must nominate a Chancellor and the group will vote, **Ja!** or **Nein!**."
            )
            await ctx.send(message)
        if decision.lower() in ['nein', 'nein!']:
            await ctx.send(f"The President **{current_president.name}** has disagreed to a veto to this policy agenda!"
                        f"\nThe current chancellor {current_chancellor.name} must enact a policy!.")
            game_state = CHANCELLOR_LEGISLATION
        return
    
@bot.command()
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
        await ctx.send(message)
    else:
        await ctx.send("Match is in progress.")

@bot.command()
@is_player()
async def reset(ctx):
    """Resets the game to allow a new round."""
    reset_game()
    await ctx.send("The game has been reset. Players can now join a new round!")

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

def get_game_dashboard():
    global players, assassinated, liberal_policies, fascist_policies, previous_president, policy_cards, discarded_policies
    message = (f"**Players:**")
    for player in players:
        message += f"\n- {player.name}"
        if (player == current_president):
            message += " (President)"
        if (player == current_chancellor):
            message += " (Chancellor)"
        if (player == previous_president):
            message += " (Previous President)"
    for player in assassinated:
        message += f"\n- {player.name} (Assassinated)"
    message += (
        f"\n\n**Policy Tracker:**"
        f"\n- Liberal Policies Enacted: {liberal_policies}/5"
        f"\n- Fascist Policies Enacted: {fascist_policies}/6"
        f"\n- Policy Deck: {len(policy_cards)}"
        f"\n- Discarded Policies: {len(discarded_policies)}"
        )
    return message

def start_new_round():
    global game_state, policy_cards, discarded_policies
    game_state = NOMINATE_CHANCELLOR
    message = None
    if len(policy_cards) < 3 and len(discarded_policies) > 0:
        policy_cards.extend(discarded_policies)
        discarded_policies.clear()
        random.shuffle(policy_cards)
        message = (f"Ran out of policy cards. Adding back all discarded policies and shuffling the deck...")
    return message

def reset_game():
    global players, game_started, roles, role_assignments, game_state, liberal_policies, fascist_policies, policy_cards, failed_election_count, previous_president, current_president, current_chancellor
    players = []
    game_started = False
    roles = []
    role_assignments = {}
    game_state = 0
    liberal_policies = 0
    fascist_policies = 0
    policy_cards = []
    failed_election_count = 0
    previous_president = None
    current_president = None
    current_chancellor = None

async def game_over(ctx, msg):
    global players, assassinated, role_assignments
    fascists = []
    liberals = []
    hitler = None
    
    # Add players from the role_assignments
    for player in players:
        if role_assignments[player]['role'] == FASCIST:
            fascists.append(player)
        if role_assignments[player]['role'] == LIBERAL:
            liberals.append(player)
        if role_assignments[player]['role'] == HITLER:
            hitler = player

    # Add players from the assassinated list
    for player in assassinated:
        if role_assignments[player]['role'] == FASCIST:
            fascists.append(player)
        if role_assignments[player]['role'] == LIBERAL:
            liberals.append(player)
        if role_assignments[player]['role'] == HITLER:
            hitler = player

    # Construct the message with the list of players in each role
    msg += f"\n\n**HITLER:**\n- {hitler.name} (assassinated)" if hitler in assassinated else f"\n\n**HITLER:**\n- {hitler.name}"
    
    msg += f"\n\n**FASCISTS:**\n" + "\n".join(f"- {fascist.name} (assassinated)" if fascist in assassinated else f"- {fascist.name}" for fascist in fascists)
    
    msg += f"\n\n**LIBERALS:**\n" + "\n".join(f"- {liberal.name} (assassinated)" if liberal in assassinated else f"- {liberal.name}" for liberal in liberals)
    
    await ctx.send(msg)
    reset_game()

# Run the bot
bot.run(DISCORD_TOKEN)
