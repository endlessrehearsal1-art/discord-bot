import os
import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import random
import asyncio

# --- CONFIGURATION ---
BOT_TOKEN = os.getenv("DISCORD_TOKEN")
OWNER_ID = 1551365165629575239

# Channel IDs
TARGET_CHANNEL_ID = 1555309550767317153
CHECKOUT_CHANNEL_ID = 1555309564805513297
TUTORIAL_CHANNEL_ID = 1555309564805513297 
INVITE_TRACKER_CHANNEL_ID = 1555309558996402296 

# Custom Emojis
VERIFIED_EMOJI = "<:verified:1555745860413956186>"
ROBUX_EMOJI = "<:robux2:1556008672709181571>"

# Images
BANNER_URL = "https://media.discordapp.net/attachments/1555309538641580103/1555760645608181800/image.jpg?backend=b2&ex=6ac1b282&is=6ac06102&hm=278e4ce0520b519d442da9266cc7733aedbb5cddbe2bd2265295060c4eaafa19&=&format=webp"
INSTRUCTION_IMAGE_URL = "https://cdn.discordapp.com/attachments/1555309538641580103/1555799290633523280/427930eb-5521-4182-a01e-2e663c380e2a.png?backend=b2&ex=6ac1d680&is=6ac08500&hm=d0a32675ea757addada072028ccb159e48c7e3bc249eecde187405232aef393c" 

# New Green Color (Vibrant Green)
NEW_GREEN = 0x00C853

# --- DATA SETUP ---
INVITE_DB = "invites.json"
GIVEAWAY_DB = "giveaways.json"

def load_data(filename):
    if not os.path.exists(filename):
        return {}
    with open(filename, "r") as f:
        return json.load(f)

def save_data(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

# --- BOT SETUP ---
intents = discord.Intents.default()
intents.message_content = True 
intents.guilds = True
intents.members = True 

bot = commands.Bot(command_prefix="!", intents=intents)
bot.invites = {} 
bot.active_giveaways = {}
loop_active = False 

# --- OWNER CHECK ---
def is_owner():
    async def predicate(interaction: discord.Interaction):
        return interaction.user.id == OWNER_ID
    return app_commands.check(predicate)

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CheckFailure):
        await interaction.response.send_message("❌ You are not authorized to use this command.", ephemeral=True)
    else:
        print(f"Error: {error}")

# --- BUTTONS ---

class InstructionView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📸 View Instructions", style=discord.ButtonStyle.primary, custom_id="view_instructions_btn")
    async def view_instructions(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📜 How To Invite Friends",
            description=f"Follow the steps in the image below to invite your friends!\n\nIf you need further help, DM <@{OWNER_ID}> {VERIFIED_EMOJI}.",
            color=NEW_GREEN
        )
        
        if INSTRUCTION_IMAGE_URL and INSTRUCTION_IMAGE_URL != "PASTE_YOUR_IMAGE_LINK_HERE":
            embed.set_image(url=INSTRUCTION_IMAGE_URL)
        else:
            embed.description = "⚠️ **Image not set!** Please tell the owner to update the image URL in the code."
            
        embed.set_footer(text="TrickOrBux • Discord Mobile")
        await interaction.response.send_message(embed=embed, ephemeral=True)

class GiveawayView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Enter Giveaway 🎉", style=discord.ButtonStyle.success, custom_id="enter_giveaway_btn")
    async def enter_giveaway(self, interaction: discord.Interaction, button: discord.ui.Button):
        msg_id = str(interaction.message.id)
        if msg_id not in bot.active_giveaways:
            await interaction.response.send_message("❌ This giveaway has ended!", ephemeral=True)
            return
        
        entries = bot.active_giveaways[msg_id]["entries"]
        if interaction.user.id in entries:
            await interaction.response.send_message("❌ You have already entered this giveaway!", ephemeral=True)
        else:
            entries.append(interaction.user.id)
            save_data(GIVEAWAY_DB, bot.active_giveaways)
            await interaction.response.send_message("✅ You have successfully entered the giveaway! Good luck!", ephemeral=True)

class EventPrizesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(
            label="How To Invite / Tutorial", 
            style=discord.ButtonStyle.link, 
            url="https://discord.com/channels/1555309413135425628/1555309564805513297"
        ))

class ClaimView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(
            label="How To Invite", 
            style=discord.ButtonStyle.link, 
            url="https://discord.com/channels/1555309413135425628/1555309564805513297"
        ))

# --- INVITE TRACKER & DM EVENTS ---
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user.name} (ID: {bot.user.id})")
    bot.add_view(InstructionView())
    bot.add_view(GiveawayView())
    bot.active_giveaways = load_data(GIVEAWAY_DB) # Load giveaways on startup
    
    for guild in bot.guilds:
        try:
            bot.invites[guild.id] = await guild.invites()
        except Exception as e:
            print(f"Failed to fetch invites for {guild.name}. Error: {e}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash command(s).")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

@bot.event
async def on_member_join(member):
    guild = member.guild
    
    # --- DM ON JOIN ---
    try:
        dm_embed = discord.Embed(
            title="Want Robux? 🤑",
            description="Well look no further! If you rack up invites, you will get Robux!",
            color=NEW_GREEN
        )
        if BANNER_URL:
            dm_embed.set_thumbnail(url=BANNER_URL)
        await member.send(embed=dm_embed)
    except discord.Forbidden:
        pass

    # --- INVITE TRACKER ---
    inviter_id = None
    inviter_name = "Unknown"
    try:
        current_invites = await guild.invites()
    except:
        current_invites = []

    for inv in current_invites:
        if inv.uses > bot.invites.get(guild.id, {}).get(inv.code, 0):
            inviter_id = inv.inviter.id
            inviter_name = inv.inviter.mention
            break

    bot.invites[guild.id] = {inv.code: inv.uses for inv in current_invites}
    channel = bot.get_channel(INVITE_TRACKER_CHANNEL_ID)

    if inviter_id:
        data = load_data(INVITE_DB)
        data[str(inviter_id)] = data.get(str(inviter_id), 0) + 1
        save_data(INVITE_DB, data)
        count = data[str(inviter_id)]
        
        if channel:
            embed = discord.Embed(
                title="🎉 New Member Joined!",
                description=f"Welcome {member.mention}!\n\n**Invited by:** {inviter_name}\n**Their Total Invites:** `{count}`",
                color=NEW_GREEN
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            if BANNER_URL: embed.set_image(url=BANNER_URL)
            await channel.send(embed=embed)
            
            if count == 3:
                await channel.send(f"🎉 {inviter_name} just hit 3 invites! DM <@{OWNER_ID}> to claim your prize!")
    else:
        if channel:
            embed = discord.Embed(
                title="🎉 New Member Joined!",
                description=f"Welcome {member.mention}!\n\n**Invited by:** Unknown",
                color=NEW_GREEN
            )
            embed.set_thumbnail(url=member.display_avatar.url)
            await channel.send(embed=embed)

# --- TASK LOOP ---
@tasks.loop(seconds=55)
async def send_claim_embed():
    global current_prize_index
    PRIZE_TIERS = [1000, 2500, 5000, 7500, 10000, 15000, 20000]
    current_prize = PRIZE_TIERS[current_prize_index]
    current_prize_index = (current_prize_index + 1) % len(PRIZE_TIERS)
    
    channel = bot.get_channel(TARGET_CHANNEL_ID)
    if channel is None: return

    embed = discord.Embed(
        description=f"## {VERIFIED_EMOJI} Someone just claimed {ROBUX_EMOJI} **{current_prize:,}** Robux\n\nA user has just received selected {ROBUX_EMOJI} **{current_prize:,}** Robux! What are you waiting for? **You only need 3 invites..**",
        color=NEW_GREEN
    )
    embed.set_footer(text="-- Partnering with Roblox 20 The Hunt --")
    if BANNER_URL: embed.set_image(url=BANNER_URL)

    try:
        await channel.send(embed=embed, view=ClaimView())
    except Exception as e:
        print(f"Error sending message: {e}")

# --- SLASH COMMANDS ---

@bot.tree.command(name="start", description="Starts the 55-second claim embed loop.")
@app_commands.default_permissions(administrator=True)
@is_owner()
async def start_loop(interaction: discord.Interaction):
    global loop_active
    if loop_active:
        send_claim_embed.cancel()
    send_claim_embed.start()
    loop_active = True
    await interaction.response.send_message("✅ Loop started! Rotating through believable prizes.", ephemeral=True)

@bot.tree.command(name="stop", description="Stops the claim embed loop.")
@app_commands.default_permissions(administrator=True)
@is_owner()
async def stop_loop(interaction: discord.Interaction):
    global loop_active
    if loop_active or send_claim_embed.is_running():
        send_claim_embed.cancel()
        loop_active = False
        await interaction.response.send_message("🛑 Loop stopped.", ephemeral=True)
    else:
        await interaction.response.send_message("The loop is not currently running.", ephemeral=True)

# --- ADVANCED PURGE COMMANDS ---
@bot.tree.command(name="purge", description="Deletes a specified number of messages (Max 1000).")
@app_commands.describe(amount="Number of messages to delete (1-1000)")
@app_commands.default_permissions(administrator=True)
@is_owner()
async def purge(interaction: discord.Interaction, amount: int):
    if amount < 1 or amount > 1000:
        await interaction.response.send_message("❌ You can only delete between 1 and 1000 messages.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    deleted = 0
    while deleted < amount:
        to_delete = min(100, amount - deleted)
        msgs = await interaction.channel.purge(limit=to_delete)
        deleted += len(msgs)
        if len(msgs) < to_delete: break
        await asyncio.sleep(1)
    await interaction.followup.send(f"🧹 Successfully deleted {deleted} messages.", ephemeral=True)

@bot.tree.command(name="purge_all", description="Deletes ALL messages in the channel (up to 1000 at a time).")
@app_commands.default_permissions(administrator=True)
@is_owner()
async def purge_all(interaction: discord.Interaction):
    await interaction.response.send_message("🧹 Purging all messages...", ephemeral=True)
    while True:
        deleted = await interaction.channel.purge(limit=100)
        if len(deleted) < 100: break
        await asyncio.sleep(1)
    await interaction.followup.send("✅ Channel completely purged!", ephemeral=True)

@bot.tree.command(name="purge_user", description="Deletes messages from a specific user.")
@app_commands.describe(member="The user to purge messages from", amount="Number of messages to check (1-100)")
@app_commands.default_permissions(administrator=True)
@is_owner()
async def purge_user(interaction: discord.Interaction, member: discord.Member, amount: int = 100):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount, check=lambda m: m.author == member)
    await interaction.followup.send(f"🧹 Deleted {len(deleted)} messages from {member.mention}.", ephemeral=True)

@bot.tree.command(name="purge_bots", description="Deletes messages from bots.")
@app_commands.describe(amount="Number of messages to check (1-100)")
@app_commands.default_permissions(administrator=True)
@is_owner()
async def purge_bots(interaction: discord.Interaction, amount: int = 100):
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount, check=lambda m: m.author.bot)
    await interaction.followup.send(f"🧹 Deleted {len(deleted)} bot messages.", ephemeral=True)

# --- GIVEAWAY COMMANDS ---
@bot.tree.command(name="gstart", description="Starts a giveaway.")
@app_commands.describe(time="Time for the giveaway (e.g., 5d, 1h, 30m)", prize="What are you giving away?")
@app_commands.default_permissions(administrator=True)
@is_owner()
async def gstart(interaction: discord.Interaction, time: str, prize: str):
    embed = discord.Embed(
        title=f"🎉 GIVEAWAY: {prize} 🎉",
        description=f"React with the button below to enter!\n\n**Ends in:** {time}",
        color=NEW_GREEN
    )
    embed.set_footer(text="Good luck to everyone!")
    await interaction.response.send_message("✅ Giveaway started!", ephemeral=True)
    msg = await interaction.channel.send(embed=embed, view=GiveawayView())
    
    bot.active_giveaways[str(msg.id)] = {
        "prize": prize,
        "entries": [],
        "channel_id": interaction.channel.id
    }
    save_data(GIVEAWAY_DB, bot.active_giveaways)

@bot.tree.command(name="gend", description="Force ends a giveaway and picks a winner.")
@app_commands.describe(message_id="The message ID of the giveaway to end", winner="The user you want to force to win (optional)")
@app_commands.default_permissions(administrator=True)
@is_owner()
async def gend(interaction: discord.Interaction, message_id: str, winner: discord.Member = None):
    msg_id = str(message_id)
    if msg_id not in bot.active_giveaways:
        await interaction.response.send_message("❌ Could not find an active giveaway with that message ID.", ephemeral=True)
        return

    giveaway = bot.active_giveaways[msg_id]
    prize = giveaway["prize"]
    entries = giveaway["entries"]
    channel = bot.get_channel(giveaway["channel_id"])
    
    if winner:
        winning_user = winner
    elif entries:
        winning_user = await bot.fetch_user(random.choice(entries))
    else:
        winning_user = interaction.user 

    embed = discord.Embed(
        title=f"🎉 GIVEAWAY ENDED: {prize} 🎉",
        description=f"The winner is {winning_user.mention}! Congratulations!",
        color=NEW_GREEN
    )
    await channel.send(embed=embed)
    del bot.active_giveaways[msg_id]
    save_data(GIVEAWAY_DB, bot.active_giveaways)
    await interaction.response.send_message(f"✅ Giveaway ended. Winner: {winning_user.mention}", ephemeral=True)

# --- NEW MODERATION & UTILITY COMMANDS ---
@bot.tree.command(name="kick", description="Kicks a member from the server.")
@app_commands.default_permissions(kick_members=True)
@is_owner()
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    await member.kick(reason=reason)
    await interaction.response.send_message(f"👢 Kicked {member.mention} for: {reason}", ephemeral=True)

@bot.tree.command(name="ban", description="Bans a member from the server.")
@app_commands.default_permissions(ban_members=True)
@is_owner()
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
    await member.ban(reason=reason)
    await interaction.response.send_message(f"🔨 Banned {member.mention} for: {reason}", ephemeral=True)

@bot.tree.command(name="timeout", description="Times out (mutes) a member.")
@app_commands.default_permissions(moderate_members=True)
@is_owner()
async def timeout(interaction: discord.Interaction, member: discord.Member, duration: int, reason: str = "No reason provided"):
    # Duration is in minutes
    from datetime import timedelta
    await member.timeout(timedelta(minutes=duration), reason=reason)
    await interaction.response.send_message(f"🔇 Timed out {member.mention} for {duration} minutes. Reason: {reason}", ephemeral=True)

@bot.tree.command(name="untimeout", description="Removes a timeout from a member.")
@app_commands.default_permissions(moderate_members=True)
@is_owner()
async def untimeout(interaction: discord.Interaction, member: discord.Member):
    await member.timeout(None)
    await interaction.response.send_message(f"🔊 Removed timeout from {member.mention}.", ephemeral=True)

@bot.tree.command(name="addrole", description="Adds a role to a member.")
@app_commands.default_permissions(manage_roles=True)
@is_owner()
async def addrole(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    await member.add_roles(role)
    await interaction.response.send_message(f"✅ Added {role.mention} to {member.mention}.", ephemeral=True)

@bot.tree.command(name="removerole", description="Removes a role from a member.")
@app_commands.default_permissions(manage_roles=True)
@is_owner()
async def removerole(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    await member.remove_roles(role)
    await interaction.response.send_message(f"✅ Removed {role.mention} from {member.mention}.", ephemeral=True)

@bot.tree.command(name="poll", description="Creates a simple yes/no poll.")
@is_owner()
async def poll(interaction: discord.Interaction, question: str):
    embed = discord.Embed(title="📊 Poll", description=question, color=NEW_GREEN)
    msg = await interaction.channel.send(embed=embed)
    await msg.add_reaction("👍")
    await msg.add_reaction("👎")
    await interaction.response.send_message("Poll created!", ephemeral=True)

@bot.tree.command(name="8ball", description="Ask the magic 8-ball a question.")
@is_owner()
async def eight_ball(interaction: discord.Interaction, question: str):
    responses = ["It is certain.", "It is decidedly so.", "Without a doubt.", "Yes definitely.", "You may rely on it.", "As I see it, yes.", "Most likely.", "Outlook good.", "Yes.", "Signs point to yes.", "Reply hazy, try again.", "Ask again later.", "Better not tell you now.", "Cannot predict now.", "Concentrate and ask again.", "Don't count on it.", "My reply is no.", "My sources say no.", "Outlook not so good.", "Very doubtful."]
    embed = discord.Embed(title="🎱 Magic 8-Ball", description=f"**Question:** {question}\n**Answer:** {random.choice(responses)}", color=NEW_GREEN)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="roll", description="Rolls a dice.")
@is_owner()
async def roll(interaction: discord.Interaction, sides: int = 6):
    result = random.randint(1, sides)
    await interaction.response.send_message(f"🎲 You rolled a **{result}** (1-{sides})", ephemeral=True)

@bot.tree.command(name="servericon", description="Shows the server icon.")
@is_owner()
async def servericon(interaction: discord.Interaction):
    if interaction.guild.icon:
        embed = discord.Embed(title=f"{interaction.guild.name}'s Icon", color=NEW_GREEN)
        embed.set_image(url=interaction.guild.icon.url)
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("This server has no icon.", ephemeral=True)

@bot.tree.command(name="banner", description="Shows your banner.")
@is_owner()
async def banner(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    user = await bot.fetch_user(member.id)
    if user.banner:
        embed = discord.Embed(title=f"{user.name}'s Banner", color=NEW_GREEN)
        embed.set_image(url=user.banner.url)
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("This user has no banner.", ephemeral=True)

# --- LEADERBOARD & TEST COMMANDS ---
@bot.tree.command(name="leaderboard", description="Shows the top 5 people with the most invites.")
async def leaderboard(interaction: discord.Interaction):
    data = load_data(INVITE_DB)
    if not data:
        await interaction.response.send_message("No invites have been tracked yet!", ephemeral=True)
        return

    sorted_users = sorted(data.items(), key=lambda x: x[1], reverse=True)[:5]
    embed = discord.Embed(title="🏆 Invite Leaderboard 🏆", description="Top 5 users with the most invites!", color=NEW_GREEN)
    medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
    
    for i, (user_id, count) in enumerate(sorted_users):
        try:
            user = await bot.fetch_user(int(user_id))
            name = user.name
        except:
            name = f"Unknown User ({user_id})"
        embed.add_field(name=f"{medals[i]} {name}", value=f"**{count}** invites", inline=False)
        
    embed.set_footer(text="Keep inviting to climb the ranks!")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="test-invite", description="Simulates a join message for the invite tracker.")
@app_commands.describe(member="The member who 'joined' (defaults to you)", inviter="The member who 'invited' them (defaults to you)")
@app_commands.default_permissions(administrator=True)
@is_owner()
async def test_invite(interaction: discord.Interaction, member: discord.Member = None, inviter: discord.Member = None):
    member = member or interaction.user
    inviter = inviter or interaction.user
    
    channel = bot.get_channel(INVITE_TRACKER_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="🎉 New Member Joined!",
            description=f"Welcome {member.mention}!\n\n**Invited by:** {inviter.mention}\n**Their Total Invites:** `3`",
            color=NEW_GREEN
        )
        embed.set_thumbnail(url=member.display_avatar.url)
        if BANNER_URL: embed.set_image(url=BANNER_URL)
        await channel.send(embed=embed)
        await channel.send(f"🎉 {inviter.mention} just hit 3 invites! DM <@{OWNER_ID}> to claim your prize!")
        await interaction.response.send_message("✅ Test invite message sent to the channel!", ephemeral=True)
    else:
        await interaction.response.send_message("❌ Invite tracker channel not found. Check the ID.", ephemeral=True)

# --- INSTRUCTIONS & EVENT PRIZES COMMANDS ---
@bot.tree.command(name="instructions", description="Sends the how-to-invite instructions embed.")
@app_commands.default_permissions(administrator=True)
@is_owner()
async def instructions(interaction: discord.Interaction):
    embed = discord.Embed(
        title="📜 How To Invite Friends",
        description=(
            "Want to earn amazing rewards? It's easy!\n\n"
            "Please click the button below to view a step-by-step visual guide on how to invite your friends to the server.\n\n"
            f"If you have any questions, feel free to DM <@{OWNER_ID}> {VERIFIED_EMOJI}!"
        ),
        color=NEW_GREEN
    )
    embed.set_footer(text="-- Partnering with Roblox 20 The Hunt --")
    await interaction.response.send_message("✅ Instructions embed sent!", ephemeral=True)
    await interaction.channel.send(embed=embed, view=InstructionView())

@bot.tree.command(name="event-prizes", description="Sends the clean event prizes embed to the current channel.")
@app_commands.default_permissions(administrator=True)
@is_owner()
async def event_prizes(interaction: discord.Interaction):
    description_text = (
        "**1️⃣ Get friends to invite!**\n"
        "**2️⃣ Get 3 invites to claim prize!**\n"
        "**3️⃣ __DM me to claim!__**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "Invite your friends to earn massive rewards!\n"
        f"To claim, **DM __<@{OWNER_ID}> {VERIFIED_EMOJI}__** with a **screenshot** of your invites.\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "# TIERS\n"
        f"**3 Invites:** __1,000__ {ROBUX_EMOJI}\n"
        f"**5 Invites:** __2,500__ {ROBUX_EMOJI}\n"
        f"**10 Invites:** __5,000__ {ROBUX_EMOJI}\n"
        f"**15 Invites:** __7,500__ {ROBUX_EMOJI}\n"
        f"**20 Invites:** __10,000__ {ROBUX_EMOJI}\n"
        f"**25 Invites:** __15,000__ {ROBUX_EMOJI}\n"
        f"**30 Invites:** __20,000__ {ROBUX_EMOJI}\n"
    )
    embed = discord.Embed(description=description_text, color=NEW_GREEN)
    embed.set_footer(text="-- Partnering with Roblox 20 The Hunt --")
    if BANNER_URL: embed.set_image(url=BANNER_URL)
    await interaction.response.send_message("✅ Event Prizes embed sent!", ephemeral=True)
    await interaction.channel.send(embed=embed, view=EventPrizesView())

# --- BASIC UTILITY COMMANDS ---
@bot.tree.command(name="embed", description="Create a custom embed.")
@app_commands.describe(title="The title of the embed", description="The main text of the embed", color="Hex color code (e.g., 00C853)")
@app_commands.default_permissions(administrator=True)
@is_owner()
async def custom_embed(interaction: discord.Interaction, title: str, description: str, color: str = "00C853"):
    try:
        color_int = int(color.replace("#", ""), 16)
    except ValueError:
        await interaction.response.send_message("❌ Invalid hex color code! Use something like `00C853`.", ephemeral=True)
        return
    embed = discord.Embed(title=title, description=description, color=color_int)
    embed.set_footer(text="Partnering with Roblox 20")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="say", description="Make the bot say something.")
@app_commands.describe(message="The message to send")
@app_commands.default_permissions(administrator=True)
@is_owner()
async def say(interaction: discord.Interaction, message: str):
    await interaction.response.send_message("Sent!", ephemeral=True)
    await interaction.channel.send(message)

@bot.tree.command(name="ping", description="Check the bot's latency.")
@app_commands.default_permissions(administrator=True)
@is_owner()
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! Latency: `{round(bot.latency * 1000)}ms`", ephemeral=True)

@bot.tree.command(name="serverinfo", description="Get information about the server.")
@app_commands.default_permissions(administrator=True)
@is_owner()
async def serverinfo(interaction: discord.Interaction):
    embed = discord.Embed(title=f"{interaction.guild.name} Info", color=NEW_GREEN)
    embed.add_field(name="Owner", value=interaction.guild.owner.mention)
    embed.add_field(name="Members", value=interaction.guild.member_count)
    embed.add_field(name="Created At", value=interaction.guild.created_at.strftime("%b %d, %Y"))
    if interaction.guild.icon: embed.set_thumbnail(url=interaction.guild.icon.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="userinfo", description="Get information about a user.")
@app_commands.describe(member="The member to get info about")
@app_commands.default_permissions(administrator=True)
@is_owner()
async def userinfo(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    embed = discord.Embed(title=f"{member.name}'s Info", color=NEW_GREEN)
    embed.add_field(name="ID", value=member.id)
    embed.add_field(name="Joined Server", value=member.joined_at.strftime("%b %d, %Y"))
    embed.add_field(name="Account Created", value=member.created_at.strftime("%b %d, %Y"))
    embed.set_thumbnail(url=member.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="avatar", description="Get a user's avatar.")
@app_commands.describe(member="The member to get the avatar of")
@app_commands.default_permissions(administrator=True)
@is_owner()
async def avatar(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    embed = discord.Embed(title=f"{member.name}'s Avatar", color=NEW_GREEN)
    embed.set_image(url=member.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# --- RUN THE BOT ---
if __name__ == "__main__":
    bot.run(BOT_TOKEN)
