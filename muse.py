# -*- coding: utf-8 -*-
import discord
from discord import app_commands
from flask import Flask, request, jsonify
import threading
from deep_translator import GoogleTranslator
from pyngrok import ngrok
import time
import speech_recognition as sr
import wave
import pyaudio
import asyncio
import atexit
from typing import Dict, Optional
from dotenv import load_dotenv
import os
from os import system
from paypalrestsdk import Payment
import stripe
# Language name mapping
languages = {
    'af': 'Afrikaans', 'sq': 'Albanian', 'am': 'Amharic', 'ar': 'Arabic',
    'hy': 'Armenian', 'az': 'Azerbaijani', 'eu': 'Basque', 'be': 'Belarusian',
    'bn': 'Bengali', 'bs': 'Bosnian', 'bg': 'Bulgarian', 'ca': 'Catalan',
    'ceb': 'Cebuano', 'ny': 'Chichewa', 'zh': 'Chinese', 'co': 'Corsican',
    'hr': 'Croatian', 'cs': 'Czech', 'da': 'Danish', 'nl': 'Dutch',
    'en': 'English', 'eo': 'Esperanto', 'et': 'Estonian', 'tl': 'Filipino',
    'fi': 'Finnish', 'fr': 'French', 'fy': 'Frisian', 'gl': 'Galician',
    'ka': 'Georgian', 'de': 'German', 'el': 'Greek', 'gu': 'Gujarati',
    'ht': 'Haitian Creole', 'ha': 'Hausa', 'haw': 'Hawaiian', 'iw': 'Hebrew',
    'hi': 'Hindi', 'hmn': 'Hmong', 'hu': 'Hungarian', 'is': 'Icelandic',
    'ig': 'Igbo', 'id': 'Indonesian', 'ga': 'Irish', 'it': 'Italian',
    'ja': 'Japanese', 'jw': 'Javanese', 'kn': 'Kannada', 'kk': 'Kazakh',
    'km': 'Khmer', 'ko': 'Korean', 'ku': 'Kurdish', 'ky': 'Kyrgyz',
    'lo': 'Lao', 'la': 'Latin', 'lv': 'Latvian', 'lt': 'Lithuanian',
    'lb': 'Luxembourgish', 'mk': 'Macedonian', 'mg': 'Malagasy', 'ms': 'Malay',
    'ml': 'Malayalam', 'mt': 'Maltese', 'mi': 'Maori', 'mr': 'Marathi',
    'mn': 'Mongolian', 'my': 'Myanmar', 'ne': 'Nepali', 'no': 'Norwegian',
    'ps': 'Pashto', 'fa': 'Persian', 'pl': 'Polish', 'pt': 'Portuguese',
    'pa': 'Punjabi', 'ro': 'Romanian', 'ru': 'Russian', 'sm': 'Samoan',
    'gd': 'Scots Gaelic', 'sr': 'Serbian', 'st': 'Sesotho', 'sn': 'Shona',
    'sd': 'Sindhi', 'si': 'Sinhala', 'sk': 'Slovak', 'sl': 'Slovenian',
    'so': 'Somali', 'es': 'Spanish', 'su': 'Sundanese', 'sw': 'Swahili',
    'sv': 'Swedish', 'tg': 'Tajik', 'ta': 'Tamil', 'te': 'Telugu',
    'th': 'Thai', 'tr': 'Turkish', 'uk': 'Ukrainian', 'ur': 'Urdu',
    'uz': 'Uzbek', 'vi': 'Vietnamese', 'cy': 'Welsh', 'xh': 'Xhosa',
    'yi': 'Yiddish', 'yo': 'Yoruba', 'zu': 'Zulu'
}
    # Language to flag mapping (common languages, can be expanded)
flag_mapping = {
    'af': '🇿🇦', 'sq': '🇦🇱', 'am': '🇪🇹', 'ar': '🇸🇦',
    'hy': '🇦🇲', 'az': '🇦🇿', 'eu': '🇪🇸', 'be': '🇧🇾',
    'bn': '🇧🇩', 'bs': '🇧🇦', 'bg': '🇧🇬', 'ca': '🇪🇸',
    'ceb': '🇵🇭', 'ny': '🇲🇼', 'zh': '🇨🇳', 'co': '🇫🇷',
    'hr': '🇭🇷', 'cs': '🇨🇿', 'da': '🇩🇰', 'nl': '🇳🇱',
    'en': '🇬🇧', 'eo': '🌍', 'et': '🇪🇪', 'tl': '🇵🇭',
    'fi': '🇫🇮', 'fr': '🇫🇷', 'fy': '🇳🇱', 'gl': '🇪🇸',
    'ka': '🇬🇪', 'de': '🇩🇪', 'el': '🇬🇷', 'gu': '🇮🇳',
    'ht': '🇭🇹', 'ha': '🇳🇬', 'haw': '🇺🇸', 'iw': '🇮🇱',
    'hi': '🇮🇳', 'hmn': '🇨🇳', 'hu': '🇭🇺', 'is': '🇮🇸',
    'ig': '🇳🇬', 'id': '🇮🇩', 'ga': '🇮🇪', 'it': '🇮🇹',
    'ja': '🇯🇵', 'jw': '🇮🇩', 'kn': '🇮🇳', 'kk': '🇰🇿',
    'km': '🇰🇭', 'ko': '🇰🇷', 'ku': '🇹🇷', 'ky': '🇰🇬',
    'lo': '🇱🇦', 'la': '🇻🇦', 'lv': '🇱🇻', 'lt': '🇱🇹',
    'lb': '🇱🇺', 'mk': '🇲🇰', 'mg': '🇲🇬', 'ms': '🇲🇾',
    'ml': '🇮🇳', 'mt': '🇲🇹', 'mi': '🇳🇿', 'mr': '🇮🇳',
    'mn': '🇲🇳', 'my': '🇲🇲', 'ne': '🇳🇵', 'no': '🇳🇴',
    'ps': '🇦🇫', 'fa': '🇮🇷', 'pl': '🇵🇱', 'pt': '🇵🇹',
    'pa': '🇮🇳', 'ro': '🇷🇴', 'ru': '🇷🇺', 'sm': '🇼🇸',
    'gd': '🇬🇧', 'sr': '🇷🇸', 'st': '🇱🇸', 'sn': '🇿🇼',
    'sd': '🇵🇰', 'si': '🇱🇰', 'sk': '🇸🇰', 'sl': '🇸🇮',
    'so': '🇸🇴', 'es': '🇪🇸', 'su': '🇮🇩', 'sw': '🇹🇿',
    'sv': '🇸🇪', 'tg': '🇹🇯', 'ta': '🇮🇳', 'te': '🇮🇳',
    'th': '🇹🇭', 'tr': '🇹🇷', 'uk': '🇺🇦', 'ur': '🇵🇰',
    'uz': '🇺🇿', 'vi': '🇻🇳', 'cy': '🇬🇧', 'xh': '🇿🇦',
    'yi': '🇮🇱', 'yo': '🇳🇬', 'zu': '🇿🇦'
}
    
class TierHandler:
    def __init__(self):
        self.premium_users = set()
        self.tiers = {
            'free': {
                'text_limit': 100,    # 100 characters per translation
                'voice_limit': 30     # 30 seconds voice translation
            },
            'premium': {
                'text_limit': float('inf'),  # Unlimited characters
                'voice_limit': 300           # 5 minutes voice translation
            }
        }
    
    def get_limits(self, user_id: int):
        return self.tiers['premium'] if user_id in self.premium_users else self.tiers['free']
# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
NGROK_TOKEN = os.getenv('NGROK_TOKEN')
tier_handler = TierHandler()
def cleanup():
    ngrok.kill()

atexit.register(cleanup)

# Set ngrok auth token
ngrok.set_auth_token(NGROK_TOKEN)

app = Flask(__name__)
intents = discord.Intents.all()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Global session tracking
hidden_sessions = set()

class UserSession:
    def __init__(self, user_id):
        self.user_id = user_id
        limits = tier_handler.get_limits(user_id)
        self.record_seconds = limits['voice_limit']
        self.frames = []
        self.active = True
        self.stream = None
        self.pyaudio = None
        self.recognizer = sr.Recognizer()
        self.chunk = 1024
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 44100
        self.record_seconds = 5

    def _audio_callback(self, in_data, frame_count, time_info, status):
        if self.active:
            self.frames.append(in_data)
        return (None, pyaudio.paContinue)

    def start_stream(self):
        self.pyaudio = pyaudio.PyAudio()
        self.stream = self.pyaudio.open(
            format=self.format,
            channels=self.channels,
            rate=self.rate,
            input=True,
            frames_per_buffer=self.chunk,
            stream_callback=self._audio_callback
        )
        self.stream.start_stream()

    def stop_stream(self):
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.pyaudio:
            self.pyaudio.terminate()
        self.active = False

class LiveVoiceTranslator:
    def __init__(self):
        self.sessions = {}

    async def _process_audio(self, session, frames, interaction, source_lang, target_lang):
        with wave.open("temp_live.wav", "wb") as wf:
            wf.setnchannels(session.channels)
            wf.setsampwidth(pyaudio.get_sample_size(session.format))
            wf.setframerate(session.rate)
            wf.writeframes(b''.join(frames))

        try:
            with sr.AudioFile("temp_live.wav") as source:
                audio = session.recognizer.record(source)
                text = session.recognizer.recognize_google(audio, language=source_lang)
                
                translator = GoogleTranslator(source=source_lang, target=target_lang)
                translated = translator.translate(text)
                
                username = interaction.user.display_name
                
                if interaction.user.id in hidden_sessions:
                    await interaction.channel.send(f"{username}: {translated}")
                else:
                    await interaction.channel.send(f"{username}: {text}\n{username} (Translated): {translated}")
        except sr.UnknownValueError:
            pass

    async def live_translate(self, interaction, user_id, source_lang, target_lang):
        session = UserSession(user_id)
        self.sessions[user_id] = session
        
        session.start_stream()
        await interaction.channel.send("🎤 Listening... Speak now!")
        
        while session.active:
            if len(session.frames) >= int(session.rate * session.record_seconds / session.chunk):
                frames = session.frames.copy()
                session.frames = []
                await self._process_audio(session, frames, interaction, source_lang, target_lang)
            await asyncio.sleep(0.1)
class TranslationServer:
    def __init__(self):
        # Single tunnel for all users
        self.main_tunnel = ngrok.connect(5000, "http", name="main")
        self.public_url = self.main_tunnel.public_url
        print(f"🌐 Main Ngrok URL: {self.public_url}")
        
        # Store user sessions
        self.translators: Dict[int, Dict[int, LiveVoiceTranslator]] = {}
        
        # Single Flask app for all users
        self.app = Flask("translation_server")
        threading.Thread(
            target=lambda: self.app.run(port=5000),
            daemon=True
        ).start()

    def get_user_url(self, user_id: int) -> str:
        # All users share the same tunnel
        return f"{self.public_url}/user/{user_id}"

    def cleanup_user(self, user_id: int):
        if user_id in self.translators:
            del self.translators[user_id]

# [Previous imports and setup remain the same]
translation_server = TranslationServer()
@tree.command(name="texttr", description="Translate text between languages")
async def text_translate(
    interaction: discord.Interaction, 
    text: str, 
    source_lang: str, 
    target_lang: str
):
    user_id = interaction.user.id
    limits = tier_handler.get_limits(user_id)
    
    if len(text) > limits['text_limit']:
        await interaction.response.send_message(
            f"🔒 Text too long! Free tier limit: {limits['text_limit']} characters\n"
            f"Use /premium to get unlimited translation!"
        )
        return
    guild_id = interaction.guild_id
    
    if guild_id not in translation_server.translators or user_id not in translation_server.translators[guild_id]:
        await interaction.response.send_message("Please use /start first to initialize your translator! 🎯")
        return
        
    try:
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        translated = translator.translate(text)
        
        username = interaction.user.display_name
        if interaction.user.id in hidden_sessions:
            await interaction.response.send_message(f"{username}: {translated}")
        else:
            await interaction.response.send_message(
                f"{username}: {text}\n"
                f"{username} (Translated): {translated}"
            )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Translation failed: {str(e)}\n"
            f"Please check your language codes (e.g., 'en' for English, 'es' for Spanish)"
        )

@tree.command(name="start", description="Start your personal translation bot")
async def start(interaction: discord.Interaction):
    user_id = interaction.user.id
    guild_id = interaction.guild_id
    
    if guild_id not in translation_server.translators:
        translation_server.translators[guild_id] = {}
    
    if user_id not in translation_server.translators[guild_id]:
        translation_server.translators[guild_id][user_id] = LiveVoiceTranslator()
        translation_server.get_user_url(user_id)
        
        await interaction.response.send_message(
            f"🎉 Welcome {interaction.user.display_name}!\n"
            f"Your personal translator is ready!\n"
            f"Available Commands:\n"
            f"1. /setchannel - Select your translation channel\n"
            f"2. /translate [source_lang] [target_lang] - Start voice translation\n"
            f"3. /texttr [text] [source_lang] [target_lang] - Translate text\n"
            f"4. /hide or /show - Toggle original text visibility\n"
            f"5. /stop - End translation session\n"
            f"6. /premium - Unlock premium features through KoFi\n"
            f"7. /status - Check your subscription status\n"
            f"7. /invite - See the bot's invite link and add to your server today!\n\n"
            f"📝 Language Codes: 'en' (English), 'es' (Spanish), 'fr' (French), 'de' (German)\n"
            f"Example: /texttr 'Hello World' en es\n"
            f"Use /list to see all supported language codes\n"
            f"JOIN OUR SERVER TO LEARN MORE: https://discord.gg/VMpBsbhrff\n",
            ephemeral=True  # This makes the message only visible to the command user
        )
        print(f"🔥 New user connected: {interaction.user.display_name}")
    else:
        await interaction.response.send_message(
            f"Your translator is already running! Ready to translate! 🚀\n"
            f"Use /translate for voice or /texttr for text translation!",
            ephemeral=True  # This makes the message only visible to the command user
        )
@tree.command(name="setchannel", description="Set the channel for translations")
async def set_channel(interaction: discord.Interaction, channel_id: str):
    try:
        channel = client.get_channel(int(channel_id))
        if channel:
            await channel.send("🚀 Translation server is connected!\nUse /translate [source_lang] [target_lang] to start\nUse /stop to end translation")
            await interaction.response.send_message(f"Successfully connected to channel {channel.name}! 🎯")
        else:
            await interaction.response.send_message("Channel not found. Please check the ID and try again! 🔍")
    except ValueError:
        await interaction.response.send_message("Please provide a valid channel ID! 🔢")

@tree.command(name="translate", description="Start live translation")
async def translate(interaction: discord.Interaction, source_lang: str, target_lang: str):
    user_id = interaction.user.id
    guild_id = interaction.guild_id
    
    # Enhanced tier handling
    tier_info = {
        "free": {
            "voice_limit": 30,
            "color": 0x95a5a6,
            "icon": "🆓",
            "features": ["Basic Translation"]
        },
        "premium": {
            "voice_limit": 120,
            "color": 0xf1c40f,
            "icon": "✨",
            "features": ["Extended Translation", "Priority Processing", "Advanced Features"]
        }
    }
    
    # Determine user's tier
    user_tier = "premium" if user_id in tier_handler.premium_users else "free"
    tier_data = tier_info[user_tier]
    limits = tier_handler.get_limits(user_id)

    if guild_id not in translation_server.translators or user_id not in translation_server.translators[guild_id]:
        await interaction.response.send_message("Please use /start first to initialize your translator! 🎯", ephemeral=True)
        return

    translator = translation_server.translators[guild_id][user_id]
    if user_id in translator.sessions:
        await interaction.response.send_message("You already have an active translation session!")
        return


    # Get proper language names
    source_name = languages.get(source_lang, source_lang)
    target_name = languages.get(target_lang, target_lang)
  
    # Get flags or use 🌐 as default
    source_flag = flag_mapping.get(source_lang, '🌐')
    target_flag = flag_mapping.get(target_lang, '🌐')

    embed = discord.Embed(
        title=f"{tier_data['icon']} Live Translation Started",
        color=tier_data['color']
    )
    
    embed.add_field(
        name="Translation Settings",
        value=f"From: {source_flag} {source_name} ({source_lang})\nTo: {target_flag} {target_name} ({target_lang})",
        inline=False
    )
    
    embed.add_field(
        name="Session Info",
        value=f"Tier: {tier_data['icon']} {user_tier.title()}\nTime Limit: ⏱️ {tier_data['voice_limit']} seconds per clip",
        inline=False
    )
    
    features_list = "\n".join([f"✓ {feature}" for feature in tier_data['features']])
    embed.add_field(
        name="Available Features",
        value=features_list,
        inline=False
    )
    
    embed.set_footer(text="🎤 Speak now to begin translation!")

    await interaction.response.send_message(embed=embed)
    await translator.live_translate(interaction, user_id, source_lang, target_lang)

@tree.command(name="hide", description="Hide original speech")
async def hide_speech(interaction: discord.Interaction):
    user_id = interaction.user.id
    hidden_sessions.add(user_id)
    await interaction.response.send_message("Original speech will be hidden! 🙈")

@tree.command(name="show", description="Show original speech")
async def show_speech(interaction: discord.Interaction):
    user_id = interaction.user.id
    hidden_sessions.discard(user_id)
    await interaction.response.send_message("Original speech will now be shown! 👀")

@tree.command(name="stop", description="Stop active translation")
async def stop_translation(interaction: discord.Interaction):
    user_id = interaction.user.id
    guild_id = interaction.guild_id
    
    await interaction.response.defer()
     
    if (guild_id in translation_server.translators and 
        user_id in translation_server.translators[guild_id] and 
        user_id in translation_server.translators[guild_id][user_id].sessions):
        
        translator = translation_server.translators[guild_id][user_id]
        translator.sessions[user_id].stop_stream()
        del translator.sessions[user_id]
        del translation_server.translators[guild_id][user_id]
        
        # Cleanup user's ngrok tunnel
        translation_server.cleanup_user(user_id)
        
        await interaction.followup.send("Translation session ended and connection closed! 🛑")
    else:
        await interaction.followup.send("No active translation session found!")
@tree.command(name="premium", description="Get premium access through Ko-fi")
async def premium(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🌟 Get Premium Access - Just $1/month!",
        description=(
            "**Premium Features**\n"
            "• Unlimited character translation\n"
            "• 5 minute voice translations\n"
            "• Priority support\n\n"
            "How to Get Premium:\n"
            "1. Click the Ko-fi button below\n"
            f"2. Include your Discord ID ({interaction.user.id}) in the message\n"
            "3. Set up monthly donation of $1\n"
            "4. Get instant premium access!"
        ),
        color=0x29abe0  # Ko-fi blue
    )
    
    view = discord.ui.View()
    view.add_item(discord.ui.Button(
        label="Subscribe on Ko-fi",
        url="https://ko-fi.com/muse/tiers",  # Replace with your Ko-fi tiers page
        style=discord.ButtonStyle.link
    ))
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
tree.command(name="premium", description="Get premium access through Ko-fi")
async def premium(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🌟 Get Premium Access - Just $1/month!",
        description=(
            "**Premium Features**\n"
            "• Unlimited character translation\n"
            "• 5 minute voice translations\n"
            "• Priority support\n\n"
            "How to Get Premium:\n"
            "1. Click the Ko-fi button below\n"
            f"2. Include your Discord ID ({interaction.user.id}) in the message\n"
            "3. Set up monthly donation of $1\n"
            "4. Get instant premium access!"
        ),
        color=0x29abe0  # Ko-fi blue
    )
    
    view = discord.ui.View()
    view.add_item(discord.ui.Button(
        label="Subscribe on Ko-fi",
        url="https://ko-fi.com/muse/tiers",  # Replace with your Ko-fi tiers page
        style=discord.ButtonStyle.link
    ))
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@app.route('/webhook/kofi', methods=['POST'])
def handle_kofi_donation():
    data = request.json
    
    if data['type'] == 'Subscription' or (data['type'] == 'Donation' and float(data['amount']) >= 1.00):
        user_id = int(data['message'])  # Users include their Discord ID in message
        tier_handler.premium_users.add(user_id)
        return {'status': 'success'}
    return {'status': 'error'}

def run_flask():
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

@tree.command(name="list", description="List all available languages for translation")
async def list_languages(interaction: discord.Interaction):
    embed = discord.Embed(
        title="Available Languages for Translation",
        description="Here are all the languages you can use with the translator:",
        color=discord.Color.blue()
    )
    
    # Sort languages alphabetically by their full names
    sorted_languages = sorted(languages.items(), key=lambda x: x[1])
    
    # Group languages by first letter
    current_letter = None
    current_field = ""
    
    for code, name in sorted_languages:
        first_letter = name[0].upper()
        
        # If we encounter a new letter, create a new field
        if first_letter != current_letter:
            if current_field:  # Add the previous field if it exists
                embed.add_field(
                    name=f"{current_letter}",
                    value=current_field,
                    inline=False
                )
            current_letter = first_letter
            current_field = ""
            
        # Get flag emoji, default to 🌐 if not found
        flag = flag_mapping.get(code, '🌐')
        # Add language entry
        current_field += f"{flag} `{code}` - {name}\n"
    
    # Add the last field
    if current_field:
        embed.add_field(
            name=f"{current_letter}",
            value=current_field,
            inline=False
        )
    
    embed.set_footer(text="Usage example: /texttr text:Hello source_lang:en target_lang:es")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="invite", description="Get the bot's invite link")
async def invite(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Invite Muse to Your Server!",
        description="Click the link below to add me to your Discord server:",
        color=0x7289da  # Discord blue color
    )
    
    embed.add_field(
        name="🔗 Invite Link",
        value="[Click Here to Invite](https://discord.com/api/oauth2/authorize?client_id=1323041248835272724&permissions=292403422272&scope=bot)",
        inline=False
    )
    
    embed.add_field(
        name="✨ Features",
        value="• Real-time voice translation\n• Text translation\n• Multiple language support\n• Custom channel settings",
        inline=False
    )
    
    embed.set_footer(text="Thanks for sharing Muse! 💖")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)
@tree.command(name="status", description="Check your subscription status")
async def check_status(interaction: discord.Interaction):
    user_id = interaction.user.id
    tier = "Premium" if user_id in tier_handler.premium_users else "Free"
    limits = tier_handler.get_limits(user_id)
    
    embed = discord.Embed(
        title="📊 Subscription Status",
        description=(
            f"**Current Tier:** {tier}\n"
            f"**Text Limit:** {limits['text_limit']} characters\n"
            f"**Voice Limit:** {limits['voice_limit']} seconds"
        ),
        color=0x2ecc71
    )
    
    await interaction.response.send_message(embed=embed, ephermal=True)   
@client.event
async def on_ready():
    print("🚀 Bot is starting up...")
    try:
        synced = await tree.sync()
        print(f"✅ Successfully synced {len(synced)} commands!")
    except Exception as e:
        print(f"🔄 Sync status: {e}")
    print("✨ Bot is ready to go!")

if 'HOSTING' in os.environ:
    # Install dependencies when deploying to cloud
    system('pip install -r requirements.txt')

if __name__ == "__main__":
    try:
        # For cloud deployment
        port = int(os.getenv('PORT', 5000))
        threading.Thread(
            target=lambda: app.run(
                host='0.0.0.0',  # Allow external connections
                port=port
            ),
            daemon=True
        ).start()
        client.run(TOKEN)
    except Exception as e:
        print(f"Startup Status: {e}")
