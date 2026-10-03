import os
import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import random

# --- CONFIGURATION ---
# The token will now be pulled securely from the hosting environment (Railway)
BOT_TOKEN = os.getenv("DISCORD_TOKEN")

# Your Owner ID
OWNER_ID = 1551365165629575239

# Channel IDs
TARGET_CHANNEL_ID = 1555309550767317153
CHECKOUT_CHANNEL_ID = 1555309564805513297
TUTORIAL_CHANNEL_ID = 1555309564805513297 
INVITE_TRACKER_CHANNEL_ID = 1555309558996402296 

# Custom Emojis provided
VERIFIED_EMOJI = "<:verified:1555745860413956186>"
ROBUX_EMOJI = "<:Robux:1555745907977232466>"

# The banner image URL you provided
BANNER_URL = "https://media.discordapp.net/attachments/1555309538641580103/1555760645608181800/image.jpg?backend=b2&ex=6ac1b282&is=6ac06102&hm=278e4ce0520b519d442da9266cc7733aedbb5cddbe2bd2265295060c4eaafa19&=&format=webp"

# --- INSTRUCTION IMAGE URL ---
INSTRUCTION_IMAGE_URL = "https://cdn.discordapp.com/attachments/1555309538641580103/1555799290633523280/427930eb-5521-4182-a01e-2e663c380e2a.png?backend=b2&ex=6ac1d680&is=6ac08500&hm=d0a32675ea757addada072028ccb159e48c7e3bc249eecde187405232aef393c" 

# --- PRIZE ROTATION SETUP ---
PRIZE_TIERS = [1000, 2500, 5000, 7500, 10000, 15000, 20000]
current_prize_index = 0

# --- GIVEAWAY DATA ---
active_giveaways = {}

# --- DATABASE SETUP ---
INVITE_DB = "invites.json"

def load_invites():
    if not os.path.exists(INVITE_DB):
        return {}
    with open(INVITE_DB, "r") as f:
        return json.load(f)

def save_invites(data):
    with open(INVITE_DB, "w") as f:
        json.dump(data, f, indent=4)

# --- BOT SETUP ---
intents = discord.Intents.default()
intents.message_content = True 
intents.guilds = True
intents.members = True 

bot = commands.Bot(command_prefix="!", intents=intents)
bot.invites = {} 

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
            description="Follow the steps in the image below to invite your friends!\n\nIf you need further help, DM <@{}> {}.".format(OWNER_ID, VERIFIED_EMOJI),
            color=0xE67E22
        )
        
        if INSTRUCTION_IMAGE_URL and INSTRUCTION_IMAGE_URL != "PASTE_YOUR_IMAGE_LINK_HERE":
            embed.set_image(url=INSTRUCTION_IMAGE_URL)
        else:
            embed.description = "⚠️ **Image not set!** Please tell the owner to update the image URL in the code."
            
        embed.set_footer(text="Halloween Rewards • Discord Mobile")
        await interaction.response.send_message(embed=embed, ephemeral=True)

class GiveawayView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Enter Giveaway 🎉", style=discord.ButtonStyle.success, custom_id="enter_giveaway_btn")
    async def enter_giveaway(self, interaction: discord.Interaction, button: discord.ui.Button):
        msg_id = interaction.message.id
        if msg_id not in active_giveaways:
            await interaction.response.send_message("❌ This giveaway has ended!", ephemeral=True)
            return
        
        entries = active_giveaways[msg_id]["entries"]
        if interaction.user.id in entries:
            await interaction.response.send_message("❌ You have already entered this giveaway!", ephemeral=True)
        else:
            entries.append(interaction.user.id)
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
            color=0xE67E22
        )
        if BANNER_URL:
            dm_embed.set_thumbnail(url=BANNER_URL)
        
        await member.send(embed=dm_embed)
    except discord.Forbidden:
        print(f"Could not DM {member.name}. They have DMs closed.")

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

    if inviter_id:
        data = load_invites()
        data[str(inviter_id)] = data.get(str(inviter_id), 0) + 1
        save_invites(data)
        count = data[str(inviter_id)]
        
        channel = bot.get_channel(INVITE_TRACKER_CHANNEL_ID)
        if channel:
            await channel.send(f"Hi {member.mention} thanks for joining! You were invited by {inviter_name}.\nThey now have **{count}** invites.")
            if count == 3:
                await channel.send(f"🎉 {inviter_name} just hit 3 invites! DM <@{OWNER_ID}> to claim your prize!")
    else:
        channel = bot.get_channel(INVITE_TRACKER_CHANNEL_ID)
        if channel:
            await channel.send(f"Hi {member.mention} thanks for joining! (Inviter unknown)")

# --- TASK LOOP ---
@tasks.loop(seconds=55)
async def send_claim_embed():
    global current_prize_index
    
    current_prize = PRIZE_TIERS[current_prize_index]
    current_prize_index = (current_prize_index + 1) % len(PRIZE_TIERS)
    
    channel = bot.get_channel(TARGET_CHANNEL_ID)
    if channel is None:
        return

    embed = discord.Embed(
        description=f"## {VERIFIED_EMOJI} Someone just claimed {ROBUX_EMOJI} **{current_prize:,}** Robux\n\nA user has just received selected {ROBUX_EMOJI} **{current_prize:,}** Robux! What are you waiting for? **You only need 3 invites..**",
        color=0xE67E22 
    )
    embed.set_footer(text="-- Partnering with Roblox 20 The Hunt --")
    if BANNER_URL:
        embed.set_image(url=BANNER_URL)

    try:
        await channel.send(embed=embed, view=ClaimView())
    except Exception as e:
        print(f"Error sending message: {e}")

# --- SLASH COMMANDS ---

@bot.tree.command(name="start", description="Starts the 55-second claim embed loop.")
@app_commands.default_permissions(administrator=True)
@is_owner()
async def start_loop(interaction: discord.Interaction):
    if send_claim_embed.is_running():
        send_claim_embed.cancel()
    send_claim_embed.start()
    await interaction.response.send_message("✅ Loop started! Rotating through believable prizes.", ephemeral=True)

@bot.tree.command(name="stop", description="Stops the claim embed loop.")
@app_commands.default_permissions(administrator=True)
@is_owner()
async def stop_loop(interaction: discord.Interaction):
    if send_claim_embed.is_running():
        send_claim_embed.cancel()
        await interaction.response.send_message("🛑 Loop stopped.", ephemeral=True)
    else:
        await interaction.response.send_message("The loop is not currently running.", ephemeral=True)

# --- GIVEAWAY COMMANDS ---
@bot.tree.command(name="gstart", description="Starts a giveaway (Timer is for show only, it won't end automatically).")
@app_commands.describe(time="Time for the giveaway (e.g., 5d, 1h, 30m)", prize="What are you giving away?")
@app_commands.default_permissions(administrator=True)
@is_owner()
async def gstart(interaction: discord.Interaction, time: str, prize: str):
    embed = discord.Embed(
        title=f"🎉 GIVEAWAY: {prize} 🎉",
        description=f"React with the button below to enter!\n\n**Ends in:** {time}",
        color=0xE67E22
    )
    embed.set_footer(text="Good luck to everyone!")
    
    await interaction.response.send_message("✅ Giveaway started!", ephemeral=True)
    msg = await interaction.channel.send(embed=embed, view=GiveawayView())
    
    active_giveaways[msg.id] = {
        "prize": prize,
        "entries": [],
        "channel_id": interaction.channel.id
    }

@bot.tree.command(name="gend", description="Force ends a giveaway and picks a winner.")
@app_commands.describe(message_id="The message ID of the giveaway to end", winner="The user you want to force to win (optional)")
@app_commands.default_permissions(administrator=True)
@is_owner()
async def gend(interaction: discord.Interaction, message_id: str, winner: discord.Member = None):
    try:
        msg_id = int(message_id)
    except ValueError:
        await interaction.response.send_message("❌ Invalid message ID.", ephemeral=True)
        return

    if msg_id not in active_giveaways:
        await interaction.response.send_message("❌ Could not find an active giveaway with that message ID.", ephemeral=True)
        return

    giveaway = active_giveaways[msg_id]
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
        color=0xE67E22
    )
    
    await channel.send(embed=embed)
    del active_giveaways[msg_id]
    await interaction.response.send_message(f"✅ Giveaway ended. Winner: {winning_user.mention}", ephemeral=True)

# --- LEADERBOARD & TEST COMMANDS ---
@bot.tree.command(name="leaderboard", description="Shows the top 5 people with the most invites.")
async def leaderboard(interaction: discord.Interaction):
    data = load_invites()
    if not data:
        await interaction.response.send_message("No invites have been tracked yet!", ephemeral=True)
        return

    sorted_users = sorted(data.items(), key=lambda x: x[1], reverse=True)[:5]
    
    embed = discord.Embed(title="🏆 Invite Leaderboard 🏆", description="Top 5 users with the most invites!", color=0xE67E22)
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
        await channel.send(f"Hi {member.mention} thanks for joining! You were invited by {inviter.mention}.\nThey now have **3** invites.")
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
        color=0xE67E22
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

    embed = discord.Embed(
        description=description_text,
        color=0xE67E22
    )

    embed.set_footer(text="-- Partnering with Roblox 20 The Hunt --")

    if BANNER_URL:
        embed.set_image(url=BANNER_URL)

    await interaction.response.send_message("✅ Event Prizes embed sent!", ephemeral=True)
    await interaction.channel.send(embed=embed, view=EventPrizesView())

# --- UTILITY COMMANDS ---
@bot.tree.command(name="purge", description="Deletes a specified number of messages.")
@app_commands.describe(amount="Number of messages to delete (1-100)")
@app_commands.default_permissions(administrator=True)
@is_owner()
async def purge(interaction: discord.Interaction, amount: int):
    if amount < 1 or amount > 100:
        await interaction.response.send_message("❌ You can only delete between 1 and 100 messages.", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=True)
    deleted = await interaction.channel.purge(limit=amount)
    await interaction.followup.send(f"🧹 Successfully deleted {len(deleted)} messages.", ephemeral=True)

@bot.tree.command(name="embed", description="Create a custom embed.")
@app_commands.describe(title="The title of the embed", description="The main text of the embed", color="Hex color code (e.g., FF0000)")
@app_commands.default_permissions(administrator=True)
@is_owner()
async def custom_embed(interaction: discord.Interaction, title: str, description: str, color: str = "E67E22"):
    try:
        color_int = int(color.replace("#", ""), 16)
    except ValueError:
        await interaction.response.send_message("❌ Invalid hex color code! Use something like `FF0000`.", ephemeral=True)
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
    embed = discord.Embed(title=f"{interaction.guild.name} Info", color=0xE67E22)
    embed.add_field(name="Owner", value=interaction.guild.owner.mention)
    embed.add_field(name="Members", value=interaction.guild.member_count)
    embed.add_field(name="Created At", value=interaction.guild.created_at.strftime("%b %d, %Y"))
    if interaction.guild.icon:
        embed.set_thumbnail(url=interaction.guild.icon.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

@bot.tree.command(name="userinfo", description="Get information about a user.")
@app_commands.describe(member="The member to get info about")
@app_commands.default_permissions(administrator=True)
@is_owner()
async def userinfo(interaction: discord.Interaction, member: discord.Member = None):
    member = member or interaction.user
    embed = discord.Embed(title=f"{member.name}'s Info", color=0xE67E22)
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
    embed = discord.Embed(title=f"{member.name}'s Avatar", color=0xE67E22)
    embed.set_image(url=member.display_avatar.url)
    await interaction.response.send_message(embed=embed, ephemeral=True)

# --- RUN THE BOT ---
if __name__ == "__main__":
    bot.run(BOT_TOKEN)