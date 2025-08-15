import os
import discord
import aiohttp
import asyncio
import logging
from dotenv import load_dotenv

# --- Added for Koyeb health check ---
from threading import Thread
from flask import Flask

app = Flask('')

@app.route('/')
def home():
    return "OK", 200

def run():
    port = int(os.getenv("PORT", 8080))  # Koyeb assigns the PORT env variable
    app.run(host="0.0.0.0", port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()
# --- End Koyeb health check code ---

# Load environment variables from .env
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO)

# === Load keys from .env ===
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')
TWITCH_CLIENT_ID = os.getenv('TWITCH_CLIENT_ID')
TWITCH_OAUTH_TOKEN = os.getenv('TWITCH_OAUTH_TOKEN')
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
DISCORD_CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID'))

# === Streamers to monitor ===
YOUTUBE_CHANNELS = {
    'K20Jose': 'UCg2aY6Ah-6i7uZv0HV2_UKg',
    'thebuffalo37': 'UCrTzhtBJCeAhUrvt00uu4tA',
    'captaincheesehead6789': 'UCfWdbEQqEjBBuSVXSaidazg',
    'Anthony-mn8tu' : 'UCMdRUDypmuIToIvRlBFVTaw',
}
TWITCH_USERS = [
    'Weaksauce85', 'falconman9999', 'coxy810', 'lonewolfgaming4k',
    'xuserlurkx', 'willmca32', 'nickisbeast20', 'kingtucker87',
    'coachclark372', 'judahrev55', 'k20jose', 'njcox18', 'Spenc205',
    'Mrinfinitytte', 'King_uchie23', 'bloodyfreddy66', 'Acreichard9','onefvsho'
]

intents = discord.Intents.default()
bot = discord.Client(intents=intents)

live_status = {
    'youtube': set(),
    'twitch': set(),
}

async def check_youtube(session):
    for name, channel_id in YOUTUBE_CHANNELS.items():
        try:
            url = (
                f"https://www.googleapis.com/youtube/v3/search?"
                f"part=snippet&channelId={channel_id}&eventType=live&type=video&key={YOUTUBE_API_KEY}"
            )
            async with session.get(url, timeout=10) as resp:
                data = await resp.json()
                if data.get("items"):
                    if name not in live_status['youtube']:
                        live_status['youtube'].add(name)
                        video_id = data['items'][0]['id']['videoId']
                        await send_discord_message(f"🎥 {name} is now live on YouTube! https://youtube.com/watch?v={video_id}")
                else:
                    live_status['youtube'].discard(name)
        except Exception as e:
            logging.error(f"Error checking YouTube for {name}: {e}")

async def check_twitch(session):
    headers = {
        'Client-ID': TWITCH_CLIENT_ID,
        'Authorization': f'Bearer {TWITCH_OAUTH_TOKEN}',
    }
    for username in TWITCH_USERS:
        try:
            url = f"https://api.twitch.tv/helix/streams?user_login={username}"
            async with session.get(url, headers=headers, timeout=10) as resp:
                data = await resp.json()
                if data.get('data'):
                    if username not in live_status['twitch']:
                        live_status['twitch'].add(username)
                        await send_discord_message(f"🎮 {username} is now live on Twitch! https://twitch.tv/{username}")
                else:
                    live_status['twitch'].discard(username)
        except Exception as e:
            logging.error(f"Error checking Twitch for {username}: {e}")

async def send_discord_message(message):
    try:
        channel = bot.get_channel(DISCORD_CHANNEL_ID)
        if channel:
            await channel.send(message)
        else:
            logging.warning("Discord channel not found.")
    except Exception as e:
        logging.error(f"Failed to send message to Discord: {e}")

async def background_loop():
    await bot.wait_until_ready()
    async with aiohttp.ClientSession() as session:
        while not bot.is_closed():
            await check_youtube(session)
            await check_twitch(session)
            await asyncio.sleep(60)  # Check every minute

@bot.event
async def on_ready():
    logging.info(f'Logged in as {bot.user.name}')
    bot.loop.create_task(background_loop())

# --- Keep-alive server must be started before bot.run() ---
keep_alive()

bot.run(DISCORD_TOKEN)
