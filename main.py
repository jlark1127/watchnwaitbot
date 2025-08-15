import os
import discord
import aiohttp
import asyncio
import logging
from dotenv import load_dotenv

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
    'Anthony-mn8tu': 'UCMdRUDypmuIToIvRlBFVTaw',
}
TWITCH_USERS = [
    'Weaksauce85', 'falconman9999', 'coxy810', 'lonewolfgaming4k',
    'xuserlurkx', 'willmca32', 'nickisbeast20', 'kingtucker87',
    'coachclark372', 'judahrev55', 'k20jose', 'njcox18', 'Spenc205',
    'Mrinfinitytte', 'King_uchie23', 'bloodyfreddy66', 'Acreichard9', 'onefvsho','straightcashnetwork317'
]

intents = discord.Intents.default()
bot = discord.Client(intents=intents)

live_status = {
    'youtube': set(),
    'twitch': set(),
}

async def check_youtube(session):
    try:
        # Step 1: Batch all channel IDs into one call
        channel_ids = list(YOUTUBE_CHANNELS.values())
        ids_str = ",".join(channel_ids)

        url = (
            f"https://www.googleapis.com/youtube/v3/channels?"
            f"part=contentDetails&id={ids_str}&key={YOUTUBE_API_KEY}"
        )
        async with session.get(url, timeout=10) as resp:
            data = await resp.json()

        uploads_playlists = {}
        for item in data.get("items", []):
            channel_id = item["id"]
            uploads_playlists[channel_id] = item["contentDetails"]["relatedPlaylists"]["uploads"]

        # Step 2: For each playlist, check recent videos
        for name, channel_id in YOUTUBE_CHANNELS.items():
            if channel_id not in uploads_playlists:
                continue

            playlist_id = uploads_playlists[channel_id]
            playlist_url = (
                f"https://www.googleapis.com/youtube/v3/playlistItems?"
                f"part=snippet&maxResults=1&playlistId={playlist_id}&key={YOUTUBE_API_KEY}"
            )
            async with session.get(playlist_url, timeout=10) as resp:
                playlist_data = await resp.json()

            if not playlist_data.get("items"):
                continue

            video_id = playlist_data["items"][0]["snippet"]["resourceId"]["videoId"]

            # Step 3: Check video liveBroadcastContent status
            video_url = (
                f"https://www.googleapis.com/youtube/v3/videos?"
                f"part=snippet,liveStreamingDetails&id={video_id}&key={YOUTUBE_API_KEY}"
            )
            async with session.get(video_url, timeout=10) as resp:
                video_data = await resp.json()

            if not video_data.get("items"):
                continue

            live_status_flag = video_data["items"][0]["snippet"].get("liveBroadcastContent", "none")

            if live_status_flag == "live":
                if name not in live_status['youtube']:
                    live_status['youtube'].add(name)
                    await send_discord_message(f"🎥 {name} is now live on YouTube! https://youtube.com/watch?v={video_id}")
            else:
                live_status['youtube'].discard(name)

    except Exception as e:
        logging.error(f"Error checking YouTube live status: {e}")


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
                        await send_discord_message(
                            f"🎮 {username} is now live on Twitch! https://twitch.tv/{username}"
                        )
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

bot.run(DISCORD_TOKEN)
