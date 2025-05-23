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
from datetime import datetime, timedelta
from langdetect import detect  
import io
from gtts import gTTS
import tempfile
from langdetect import detect
import discord.ext.voice_recv as voice_recv
from discord.ext.voice_recv.sinks import BasicSink
import logging
import tempfile
import threading
import queue
# Language name mapping
languages = {
    'af': 'Afrikaans', 'sq': 'Albanian', 'am': 'Amharic', 'ar': 'Arabic',
    'hy': 'Armenian', 'az': 'Azerbaijani', 'eu': 'Basque', 'be': 'Belarusian',
    'bn': 'Bengali', 'bs': 'Bosnian', 'bg': 'Bulgarian', 'ca': 'Catalan',
    'ceb': 'Cebuano', 'ny': 'Chichewa', 'zh-CN': 'Chinese', 'zh-TW': 'Chinese (Traditional)', 'co': 'Corsican',
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
    'ceb': '🇵🇭', 'ny': '🇲🇼', 'zh-CN': '🇨🇳', 'zh-TW': '🇹🇼','co': '🇫🇷',
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
                'voice_limit': 30     # 30 minutes voice translation
            },
            'premium': {
                'text_limit': float('inf'),  # Unlimited characters
                'voice_limit': float('inf')           # infinite voice translation
            }
        }
    
    def get_limits(self, user_id: int):
        return self.tiers['premium'] if user_id in self.premium_users else self.tiers['free']
# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
NGROK_TOKEN = os.getenv('NGROK_TOKEN')
tier_handler = TierHandler()
tier_handler.premium_users.add(1192196672437096520) 
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
voice_translation_sessions = {}
class UserUsage:
    def __init__(self):
        self.daily_usage = {}  # {user_id: {'usage': seconds, 'last_reset': datetime}}
        
    def add_usage(self, user_id: int, seconds: int) -> None:
        current_time = datetime.now()
        
        # Initialize or reset if it's a new day
        if (user_id not in self.daily_usage or 
            current_time.date() > self.daily_usage[user_id]['last_reset'].date()):
            self.daily_usage[user_id] = {
                'usage': 0,
                'last_reset': current_time
            }
            
        self.daily_usage[user_id]['usage'] += seconds
        
    def get_remaining_time(self, user_id: int, is_premium: bool) -> int:
        if is_premium:
            return float('inf')  # Unlimited for premium users
            
        current_time = datetime.now()
        
        # If no usage today or it's a new day
        if (user_id not in self.daily_usage or 
            current_time.date() > self.daily_usage[user_id]['last_reset'].date()):
            return 1800  # 30 minutes in seconds
            
        used_time = self.daily_usage[user_id]['usage']
        remaining = max(1800 - used_time, 0)  # 30 minutes minus usage
        return remaining
usage_tracker = UserUsage()
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

# Create a reverse mapping from language names to codes
language_names_to_codes = {name.lower(): code for code, name in languages.items()}

# Add this function to replace the existing get_language_code function
def get_language_code(lang_input):
    """Convert language name or code to a valid language code"""
    lang_input = lang_input.lower().strip()
    
    # If it's already a valid code, return it
    if lang_input in languages:
        return lang_input
    
    # Handle special cases for Chinese
    if lang_input in ['chinese', 'zh', 'zh-cn', 'mandarin']:
        return 'zh-CN'
    
    # If it's a language name, convert to code
    if lang_input in language_names_to_codes:
        return language_names_to_codes[lang_input]
        
    # Try partial matching for language names
    for name, code in language_names_to_codes.items():
        if lang_input in name:
            return code
    
    # Try matching against language codes with special characters
    for code, name in languages.items():
        if lang_input == code.lower() or lang_input == name.lower():
            return code
            
    # Not found
    return None

@tree.command(name="start", description="Start your personal translation bot")
async def start(interaction: discord.Interaction):
    user_id = interaction.user.id
    guild_id = interaction.guild_id
    
    if guild_id not in translation_server.translators:
        translation_server.translators[guild_id] = {}
    
    if user_id not in translation_server.translators[guild_id]:
        translation_server.translators[guild_id][user_id] = {}  # Simple dictionary instead of LiveVoiceTranslator
        translation_server.get_user_url(user_id)
        
        # Create welcome embed
        embed = discord.Embed(
            title="🎉 Welcome to Muse Translator!",
            description=f"Hello {interaction.user.display_name}! Your personal translator is ready to use.",
            color=0x3498db
        )
        
        # Add command categories
        embed.add_field(
            name="🗣️ Voice Commands",
            value=(
                "`/voicechat [source] [target]` - Real-time voice chat translation\n"
                "`/voice [text] [source] [target]` - Text to speech translation\n"
                "`/speak [text] [source] [target]` - Translate and play in voice channel"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📝 Text Commands",
            value=(
                "`/texttr [text] [source] [target]` - Translate text\n"
                "`/autotranslate [source] [target]` - Auto-translate all your messages\n"
                "`/read [message_id] [target]` - Translate any sent message by ID"
            ),
            inline=False
        )
        
        embed.add_field(
            name="⚙️ Settings",
            value=(
                "`/setchannel` - Select your translation channel\n"
                "`/hide` or `/show` - Toggle original text visibility\n"
                "`/stop` - End translation session"
            ),
            inline=False
        )
        
        embed.add_field(
            name="ℹ️ Information",
            value=(
                "`/list` - See all supported languages\n"
                "`/premium` - Unlock premium features\n"
                "`/status` - Check your subscription status\n"
                "`/invite` - Get the bot's invite link"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📝 Language Format",
            value=(
                "You can use language names or codes:\n"
                "• Names: `English`, `Spanish`, `Japanese`\n"
                "• Codes: `en`, `es`, `ja`\n"
                "• Example: `/texttr 'Hello World' English Spanish`"
            ),
            inline=False
        )
        
        # Add footer with server invite
        embed.set_footer(text="Join our support server: https://discord.gg/VMpBsbhrff")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        print(f"🔥 New user connected: {interaction.user.display_name}")
    else:
        # Create already running embed
        embed = discord.Embed(
            title="🚀 Translator Already Running",
            description="Your translator is already active and ready to use!",
            color=0x2ecc71
        )
        
        embed.add_field(
            name="Quick Commands",
            value=(
                "`/voicechat` - Start voice translation\n"
                "`/texttr` - Translate text\n"
                "`/autotranslate` - Auto-translate your messages\n"
                "`/stop` - End translation session"
            ),
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
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
@tree.command(name="texttr", description="Translate text between languages")
async def text_translate(
    interaction: discord.Interaction, 
    text: str, 
    source_lang: str, 
    target_lang: str
):
    user_id = interaction.user.id
    limits = tier_handler.get_limits(user_id)
    
    # Convert language inputs to codes
    source_code = get_language_code(source_lang)
    target_code = get_language_code(target_lang)
    
    # Validate language codes
    if not source_code:
        await interaction.response.send_message(
            f"❌ Invalid source language: '{source_lang}'\nUse /list to see available languages.",
            ephemeral=True
        )
        return
        
    if not target_code:
        await interaction.response.send_message(
            f"❌ Invalid target language: '{target_lang}'\nUse /list to see available languages.",
            ephemeral=True
        )
        return
    
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
        translator = GoogleTranslator(source=source_code, target=target_code)
        translated = translator.translate(text)
        
        # Get proper language names and flags
        source_name = languages.get(source_code, source_code)
        target_name = languages.get(target_code, target_code)
        source_flag = flag_mapping.get(source_code, '🌐')
        target_flag = flag_mapping.get(target_code, '🌐')
        
        username = interaction.user.display_name
        
        # Create embed with appropriate fields based on hidden status
        embed = discord.Embed(
            title="Text Translation",
            color=0x3498db
        )
        
        if interaction.user.id in hidden_sessions:
            # Only show translation in hidden mode
            embed.add_field(
                name=f"{target_flag} Translation ({target_name})",
                value=translated,
                inline=False
            )
        else:
            # Show both original and translation
            embed.add_field(
                name=f"{source_flag} Original ({source_name})",
                value=text,
                inline=False
            )
            
            embed.add_field(
                name=f"{target_flag} Translation ({target_name})",
                value=translated,
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Translation failed: {str(e)}\n"
            f"Please check your language codes (e.g., 'en' for English, 'es' for Spanish)"
        )
@tree.command(name="voice", description="Translate text and convert to speech")
async def translate_and_speak(
    interaction: discord.Interaction,
    text: str,
    source_lang: str,
    target_lang: str
):
    try:
        # Check if command is used in a guild
        if not interaction.guild:
            embed = discord.Embed(
                title="❌ Server Only Command",
                description="This command can only be used if I'm invited to the server!\n"
                "🔗 Use `/invite` to get the proper invite link",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Convert language inputs to codes
        source_code = get_language_code(source_lang)
        target_code = get_language_code(target_lang)
        
        # Validate language codes
        if not source_code:
            await interaction.response.send_message(
                f"❌ Invalid source language: '{source_lang}'\nUse /list to see available languages.",
                ephemeral=True
            )
            return
            
        if not target_code:
            await interaction.response.send_message(
                f"❌ Invalid target language: '{target_lang}'\nUse /list to see available languages.",
                ephemeral=True
            )
            return

        # Get user's tier limits
        user_id = interaction.user.id
        limits = tier_handler.get_limits(user_id)
        
        # Check text length against limits
        if len(text) > limits['text_limit']:
            await interaction.response.send_message(
                f"🔒 Text too long! Free tier limit: {limits['text_limit']} characters\n"
                f"Use /premium to get unlimited translation!",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        
        # Don't translate if source and target are the same
        if source_code == target_code:
            translated_text = text
        else:
            # Translate the text
            translator = GoogleTranslator(source=source_code, target=target_code)
            translated_text = translator.translate(text)

        # Create temporary file using BytesIO instead of a file
        mp3_fp = io.BytesIO()
        tts = gTTS(text=translated_text, lang=target_code)
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
            
        # Get language names and flags
        source_name = languages.get(source_code, source_code)
        target_name = languages.get(target_code, target_code)
        source_flag = flag_mapping.get(source_code, '🌐')
        target_flag = flag_mapping.get(target_code, '🌐')
            
        # Create embed
        embed = discord.Embed(
            title="Text Translation & Speech",
            color=0x3498db
        )
            
        embed.add_field(
            name=f"{source_flag} Original ({source_name})",
            value=text,
            inline=False
        )
            
        embed.add_field(
            name=f"{target_flag} Translation ({target_name})",
            value=translated_text,
            inline=False
        )
            
        # Send the embed as ephemeral
        await interaction.followup.send(
            embed=embed,
            ephemeral=True
        )

        # Send the audio file publicly in the channel
        await interaction.channel.send(
            file=discord.File(mp3_fp, filename='translated_speech.mp3')
        )
        
        # Close the BytesIO buffer
        mp3_fp.close()

    except Exception as e:
        if not interaction.response.is_done():
            await interaction.response.send_message(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('muse')

@tree.command(name="voicechat", description="Translate voice chat in real-time")
async def voice_chat_translate(
    interaction: discord.Interaction, 
    source_lang: str,
    target_lang: str
):
    # Check if command is used in a guild
    if not interaction.guild:
        embed = discord.Embed(
            title="❌ Server Only Command",
            description="This command can only be used if I'm invited to the server!",
            color=0xFF0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
        
    # Check if user is in a voice channel
    if not interaction.user.voice:
        await interaction.response.send_message(
            "❌ You need to be in a voice channel to use this command!",
            ephemeral=True
        )
        return
        
    # Convert language inputs to codes - support both codes and names
    source_code = "auto" if source_lang.lower() == "auto" else get_language_code(source_lang)
    target_code = get_language_code(target_lang)
    
    # Validate language codes
    if source_lang.lower() != "auto" and not source_code:
        await interaction.response.send_message(
            f"❌ Invalid source language: '{source_lang}'\nUse /list to see available languages or use 'auto' for automatic detection.",
            ephemeral=True
        )
        return
        
    if not target_code:
        await interaction.response.send_message(
            f"❌ Invalid target language: '{target_lang}'\nUse /list to see available languages.",
            ephemeral=True
        )
        return
        
    # Get user's tier limits
    user_id = interaction.user.id
    limits = tier_handler.get_limits(user_id)
    
    voice_channel = interaction.user.voice.channel
    
    # Define the TranslationSink class
    class TranslationSink(BasicSink):
        def __init__(self, *, source_language, target_language, text_channel, client_instance):
            # Must call super().__init__() as per documentation
            self.event = asyncio.Event()
            super().__init__(self.event)
            self.source_language = source_language
            self.target_language = target_language
            self.text_channel = text_channel
            self.client_instance = client_instance
            self.user_buffers = {}
            self.processing_queue = queue.Queue()
            self.is_running = True
            self.processing_thread = threading.Thread(target=self._process_audio)
            self.processing_thread.start()
            logger.info("TranslationSink initialized")
            
        # Specify that we want PCM data, not opus
        def wants_opus(self) -> bool:
            return False
            
        def write(self, user, data):
            # Extract user ID and PCM data from the VoiceData object
            user_id = user.id if hasattr(user, 'id') else str(user)
            
            # Check if we have PCM data
            if not hasattr(data, 'pcm'):
                return  # Skip if no PCM data
                
            pcm_data = data.pcm
            if not pcm_data:
                return  # Skip if PCM data is empty
            
            # Buffer audio data by user
            if user_id not in self.user_buffers:
                self.user_buffers[user_id] = []
                logger.info(f"New user buffer created for user {user_id}")
            
            self.user_buffers[user_id].append(pcm_data)
            
            # If we have enough data (about 2 seconds of audio), process it
            if len(self.user_buffers[user_id]) >= 100:  # ~2 seconds at 20ms chunks
                logger.info(f"Processing audio buffer for user {user_id}")
                audio_buffer = b''.join(self.user_buffers[user_id])
                self.user_buffers[user_id] = []
                self.processing_queue.put((user_id, audio_buffer))
                
        def _process_audio(self):
            logger.info("Audio processing thread started")
            while self.is_running:
                try:
                    # Get audio data from queue with timeout
                    user_id, audio_buffer = self.processing_queue.get(timeout=0.5)
                    logger.info(f"Got audio data from queue for user {user_id}")
                    
                    # Create a temporary WAV file
                    with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                        temp_filename = temp_file.name
                        
                    # Write audio data to WAV file
                    with wave.open(temp_filename, 'wb') as wf:
                        wf.setnchannels(2)  # Stereo
                        wf.setsampwidth(2)  # 2 bytes per sample (16-bit)
                        wf.setframerate(48000)  # 48 kHz
                        wf.writeframes(audio_buffer)
                    
                    logger.info(f"Created WAV file: {temp_filename}")
                    
                    # Process in a separate thread to avoid blocking
                    threading.Thread(
                        target=self._transcribe_and_translate,
                        args=(temp_filename, user_id)
                    ).start()
                    
                except queue.Empty:
                    continue
                except Exception as e:
                    logger.error(f"Error processing audio: {e}")
        
        async def _send_translation(self, user_id, original_text, translated_text, detected_lang=None):
            try:
                # Get user from guild
                guild = self.text_channel.guild
                member = await guild.fetch_member(user_id)
                
                if not member:
                    return
                    
                username = member.display_name
                logger.info(f"Sending translation for user {username}")
                
                # Get source language - either detected or specified
                source_lang = detected_lang if detected_lang else self.source_language
                source_name = languages.get(source_lang, source_lang)
                target_name = languages.get(self.target_language, self.target_language)
                
                source_flag = flag_mapping.get(source_lang, '🌐')
                target_flag = flag_mapping.get(self.target_language, '🌐')
                
                # Create embed
                embed = discord.Embed(
                    title=f"🎤 Voice Translation: {username}",
                    color=0x3498db
                )
                
                if user_id not in hidden_sessions:
                    embed.add_field(
                        name=f"{source_flag} Original ({source_name})",
                        value=original_text,
                        inline=False
                    )
                
                embed.add_field(
                    name=f"{target_flag} Translation ({target_name})",
                    value=translated_text,
                    inline=False
                )
                
                await self.text_channel.send(embed=embed)
                logger.info("Translation sent successfully")
                
            except Exception as e:
                logger.error(f"Error sending translation: {e}")
        
        def _transcribe_and_translate(self, filename, user_id):
            try:
                logger.info(f"Transcribing audio for user {user_id}")
                # Use speech recognition to transcribe
                recognizer = sr.Recognizer()
                with sr.AudioFile(filename) as source:
                    audio = recognizer.record(source)
                    
                    # Try to recognize speech
                    try:
                        # Use specified source language if not auto
                        if self.source_language != "auto":
                            text = recognizer.recognize_google(audio, language=self.source_language)
                            detected_lang = self.source_language
                        else:
                            text = recognizer.recognize_google(audio)
                            # Try to detect language from text
                            try:
                                detected_lang = detect(text)
                            except:
                                detected_lang = "auto"
                        
                        logger.info(f"Recognized text: {text}")
                        
                        # Only process if we got actual text
                        if text and len(text.strip()) > 0:
                            # Translate the text
                            translator = GoogleTranslator(source=self.source_language if self.source_language != "auto" else "auto", 
                                                         target=self.target_language)
                            translated = translator.translate(text)
                            logger.info(f"Translated text: {translated}")
                            
                            # Send to Discord
                            asyncio.run_coroutine_threadsafe(
                                self._send_translation(user_id, text, translated, detected_lang),
                                self.client_instance.loop
                            )
                    except sr.UnknownValueError:
                        # Speech was unintelligible
                        logger.info("Speech was unintelligible")
                        pass
                    except Exception as e:
                        logger.error(f"Error in speech recognition: {e}")
            
            except Exception as e:
                logger.error(f"Error transcribing audio: {e}")
            finally:
                # Clean up temp file
                try:
                    os.unlink(filename)
                except:
                    pass
        
        def cleanup(self):
            logger.info("Cleaning up TranslationSink")
            self.is_running = False
            if hasattr(self, 'processing_thread') and self.processing_thread.is_alive():
                self.processing_thread.join(timeout=2.0)
                
        # Add sink event listeners as per documentation
        @BasicSink.listener()
        def on_voice_member_speaking_start(self, member):
            logger.info(f"Member started speaking: {member.display_name}")
            
        @BasicSink.listener()
        def on_voice_member_speaking_stop(self, member):
            logger.info(f"Member stopped speaking: {member.display_name}")
    
    # Connect to the voice channel
    try:
        await interaction.response.defer(ephemeral=True)
        logger.info(f"Connecting to voice channel: {voice_channel.name}")
        
        # First, check if we're already connected to a voice channel in this guild
        if interaction.guild.voice_client:
            # If we're in a different channel, move to the new one
            if interaction.guild.voice_client.channel != voice_channel:
                logger.info(f"Moving to different voice channel: {voice_channel.name}")
                await interaction.guild.voice_client.move_to(voice_channel)
                
            # If the existing client is not a VoiceRecvClient, disconnect and reconnect
            if not isinstance(interaction.guild.voice_client, voice_recv.VoiceRecvClient):
                logger.info("Existing client is not a VoiceRecvClient, reconnecting")
                await interaction.guild.voice_client.disconnect()
                voice_client = await voice_channel.connect(cls=voice_recv.VoiceRecvClient, self_deaf=False)
            else:
                voice_client = interaction.guild.voice_client
        else:
            # Connect to voice channel with the correct class parameter
            logger.info(f"Connecting to voice channel with VoiceRecvClient: {voice_channel.name}")
            voice_client = await voice_channel.connect(cls=voice_recv.VoiceRecvClient, self_deaf=False)
            
        # Wait a moment to ensure connection is established
        await asyncio.sleep(2)
            
        # Check if connection was successful
        if not voice_client.is_connected():
            logger.error("Voice client not connected after connection attempt")
            await interaction.followup.send(
                "❌ Failed to connect to voice channel. Please try again.",
                ephemeral=True
            )
            return
            
        logger.info(f"Voice client connected: {voice_client.is_connected()}")
        
        # Create our custom sink
        logger.info("Creating TranslationSink")
        sink = TranslationSink(
            source_language=source_code,
            target_language=target_code,
            text_channel=interaction.channel,
            client_instance=client
        )
        logger.info("Successfully created TranslationSink")
        
        # Start listening with explicit error handling
        try:
            logger.info("Starting to listen")
            
            # Check if already listening
            if voice_client.is_listening():
                logger.info("Already listening, stopping first")
                voice_client.stop_listening()
                await asyncio.sleep(1)
            
            # Start listening
            voice_client.listen(sink)
            logger.info("Successfully started listening")
            
            # Get proper language names and flags for display
            source_display = "Auto-detect" if source_code == "auto" else languages.get(source_code, source_code)
            target_display = languages.get(target_code, target_code)
            source_flag = '🔍' if source_code == "auto" else flag_mapping.get(source_code, '🌐')
            target_flag = flag_mapping.get(target_code, '🌐')
            
            # Check if user is premium
            is_premium = user_id in tier_handler.premium_users
            
            # Create embed with appropriate styling
            embed = discord.Embed(
                title="🎤 Voice Chat Translation Started",
                description=(
                    f"Now translating voice chat from {source_flag} {source_display} to {target_flag} {target_display}.\n"
                    f"Speak clearly for best results.\n"
                    f"Use `/stop` to end the translation session."
                ),
                color=0xf1c40f if is_premium else 0x3498db
            )
            
            # Add footer about auto-disconnect
            embed.set_footer(text="Bot will automatically leave when everyone exits the voice channel")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Store the voice client and sink for later cleanup
            if interaction.guild_id not in voice_translation_sessions:
                voice_translation_sessions[interaction.guild_id] = {}
                
            voice_translation_sessions[interaction.guild_id] = {
                'voice_client': voice_client,
                'sink': sink,
                'channel': voice_channel
            }
            
            # Start a task to check if users leave the voice channel
            client.loop.create_task(check_voice_channel(voice_client, voice_channel))
                
        except Exception as e:
            logger.error(f"Error starting listening: {e}")
            await interaction.followup.send(
                f"❌ Error starting listening: {str(e)}",
                ephemeral=True
            )
            
    except Exception as e:
        logger.error(f"Error connecting to voice: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message(
                f"❌ Error starting voice translation: {str(e)}",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"❌ Error starting voice translation: {str(e)}",
                ephemeral=True
            )
@tree.command(name="speak", description="Translate text and play speech in voice channel")
async def translate_and_speak(
    interaction: discord.Interaction,
    text: str,
    source_lang: str,
    target_lang: str
):
    try:
        # Check if command is used in a guild
        if not interaction.guild:
            embed = discord.Embed(
                title="❌ Server Only Command",
                description="This command can only be used if I'm invited to the server!\n"
                "🔗 Use `/invite` to get the proper invite link",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Check if user is in a voice channel
        if not interaction.user.voice:
            await interaction.response.send_message(
                "❌ You need to be in a voice channel to use this command!",
                ephemeral=True
            )
            return

        # Convert language inputs to codes
        source_code = get_language_code(source_lang)
        target_code = get_language_code(target_lang)
        
        # Validate language codes
        if not source_code:
            await interaction.response.send_message(
                f"❌ Invalid source language: '{source_lang}'\nUse /list to see available languages.",
                ephemeral=True
            )
            return
            
        if not target_code:
            await interaction.response.send_message(
                f"❌ Invalid target language: '{target_lang}'\nUse /list to see available languages.",
                ephemeral=True
            )
            return

        # Get user's tier limits
        user_id = interaction.user.id
        limits = tier_handler.get_limits(user_id)
        
        # Check text length against limits
        if len(text) > limits['text_limit']:
            await interaction.response.send_message(
                f"🔒 Text too long! Free tier limit: {limits['text_limit']} characters\n"
                f"Use /premium to get unlimited translation!",
                ephemeral=True
            )
            return

        await interaction.response.defer(ephemeral=True)
        
        # Don't translate if source and target are the same
        if source_code == target_code:
            translated_text = text
        else:
            # Translate the text
            translator = GoogleTranslator(source=source_code, target=target_code)
            translated_text = translator.translate(text)

        # Create temporary file using BytesIO
        mp3_fp = io.BytesIO()
        tts = gTTS(text=translated_text, lang=target_code)
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        
        # Save to a temporary file for voice playback
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
            temp_filename = temp_file.name
            mp3_fp.seek(0)
            temp_file.write(mp3_fp.read())
            
        # Get language names and flags
        source_name = languages.get(source_code, source_code)
        target_name = languages.get(target_code, target_code)
        source_flag = flag_mapping.get(source_code, '🌐')
        target_flag = flag_mapping.get(target_code, '🌐')
            
        # Create embed
        embed = discord.Embed(
            title="Text Translation & Speech",
            color=0x3498db
        )
            
        embed.add_field(
            name=f"{source_flag} Original ({source_name})",
            value=text,
            inline=False
        )
            
        embed.add_field(
            name=f"{target_flag} Translation ({target_name})",
            value=translated_text,
            inline=False
        )
            
        # Send the embed as ephemeral
        await interaction.followup.send(
            embed=embed,
            ephemeral=True
        )

        # Connect to voice channel and play audio
        try:
            voice_channel = interaction.user.voice.channel
            voice_client = interaction.guild.voice_client
            
            # Connect to voice channel if not already connected
            if voice_client is None:
                voice_client = await voice_channel.connect()
            elif voice_client.channel != voice_channel:
                await voice_client.move_to(voice_channel)
            
            # Stop any currently playing audio
            if voice_client.is_playing():
                voice_client.stop()
            
            # Start a task to check if users leave the voice channel
            client.loop.create_task(check_voice_channel(voice_client, voice_channel))
            
            try:
                # Check if FFmpeg is available
                import subprocess
                try:
                    subprocess.run(["ffmpeg", "-version"], check=True, capture_output=True)
                    ffmpeg_available = True
                except (subprocess.SubprocessError, FileNotFoundError):
                    ffmpeg_available = False
                
                if not ffmpeg_available:
                    # FFmpeg not found, send the file instead
                    await interaction.channel.send(
                        "⚠️ Voice playback unavailable (FFmpeg not installed). Sending audio file instead:",
                        file=discord.File(temp_filename, filename='translated_speech.mp3')
                    )
                    # Clean up the temp file after sending
                    try:
                        os.unlink(temp_filename)
                    except:
                        pass
                    return
                
                # Create FFmpeg audio source with explicit executable path
                # Try with default path first
                try:
                    audio_source = discord.FFmpegPCMAudio(temp_filename)
                except Exception as e1:
                    error_message = str(e1)
                    await interaction.followup.send(
                        f"⚠️ FFmpeg error: {error_message}\nTrying to send file instead...",
                        ephemeral=True
                    )
                    # Send the file as fallback
                    await interaction.channel.send(
                        "⚠️ Voice playback failed. Sending audio file instead:",
                        file=discord.File(temp_filename, filename='translated_speech.mp3')
                    )
                    # Clean up the temp file after sending
                    try:
                        os.unlink(temp_filename)
                    except:
                        pass
                    return
                
                # Play the audio
                voice_client.play(audio_source, after=lambda e: asyncio.run_coroutine_threadsafe(
                    cleanup_after_playback(temp_filename, voice_client), client.loop))
                
                # Send a public message that audio is playing
                await interaction.followup.send(f"🔊 Playing translated audio in {voice_channel.name}", ephemeral=True)
            except Exception as e:
                # Get detailed error information
                error_message = str(e)
                await interaction.followup.send(
                    f"⚠️ Detailed error: {error_message}\nSending audio file instead...",
                    ephemeral=True
                )
                # Send the file as fallback
                await interaction.channel.send(
                    "⚠️ Voice playback failed. Sending audio file instead:",
                    file=discord.File(temp_filename, filename='translated_speech.mp3')
                )
                # Clean up the temp file after sending
                try:
                    os.unlink(temp_filename)
                except:
                    pass
            
        except Exception as e:
            # Clean up the temp file if voice playback fails
            try:
                os.unlink(temp_filename)
            except:
                pass
            await interaction.followup.send(
                f"❌ Failed to play audio: {str(e)}",
                ephemeral=True
            )
        
        # Close the BytesIO buffer
        mp3_fp.close()

    except Exception as e:
        if not interaction.response.is_done():
            await interaction.response.send_message(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )

# Add this function to check if users leave the voice channel
async def check_voice_channel(voice_client, voice_channel):
    """Check if users leave the voice channel and disconnect the bot if it's alone"""
    if not voice_client or not voice_client.is_connected():
        return
        
    while voice_client.is_connected():
        # Count members in the voice channel (excluding the bot)
        member_count = sum(1 for member in voice_channel.members if not member.bot)
        
        # If no human members are left, disconnect
        if member_count == 0:
            await voice_client.disconnect()
            print(f"🔇 Disconnected from {voice_channel.name} - everyone left")
            break
            
        # Check every 5 seconds
        await asyncio.sleep(5)

# Make sure this function exists for the audio cleanup
async def cleanup_after_playback(filename, voice_client):
    """Clean up the temporary file after playback"""
    try:
        os.unlink(filename)
    except:
        pass
    
# Dictionary to track users with auto-translation enabled
auto_translate_users = {}  # Format: {user_id: {'source': source_code, 'target': target_code}}

@tree.command(name="autotranslate", description="Automatically translate all your messages")
async def auto_translate(
    interaction: discord.Interaction,
    source_lang: str,
    target_lang: str
):
    user_id = interaction.user.id
    guild_id = interaction.guild_id
    
    # Convert language inputs to codes
    source_code = "auto" if source_lang.lower() == "auto" else get_language_code(source_lang)
    target_code = get_language_code(target_lang)
    
    # Validate language codes
    if source_lang.lower() != "auto" and not source_code:
        await interaction.response.send_message(
            f"❌ Invalid source language: '{source_lang}'\nUse /list to see available languages or use 'auto' for automatic detection.",
            ephemeral=True
        )
        return
        
    if not target_code:
        await interaction.response.send_message(
            f"❌ Invalid target language: '{target_lang}'\nUse /list to see available languages.",
            ephemeral=True
        )
        return
    
    # Store user's auto-translation preferences
    auto_translate_users[user_id] = {
        'source': source_code,
        'target': target_code,
        'guild_id': guild_id,
        'channel_id': interaction.channel_id
    }
    
    # Get proper language names and flags for display
    source_display = "Auto-detect" if source_code == "auto" else languages.get(source_code, source_code)
    target_display = languages.get(target_code, target_code)
    source_flag = '🔍' if source_code == "auto" else flag_mapping.get(source_code, '🌐')
    target_flag = flag_mapping.get(target_code, '🌐')
    
    await interaction.response.send_message(
        f"✅ Auto-translation enabled!\n"
        f"All your messages will be translated from {source_flag} {source_display} to {target_flag} {target_display}.\n"
        f"Use `/stop` to disable auto-translation.",
        ephemeral=True
    )

@client.event
async def on_message(message):
    # Ignore messages from bots to prevent loops
    if message.author.bot:
        return
    
    # Check if user has auto-translation enabled
    user_id = message.author.id
    if user_id in auto_translate_users:
        settings = auto_translate_users[user_id]
        
        # Only translate in the same guild and channel where it was enabled
        if message.guild.id == settings['guild_id'] and message.channel.id == settings['channel_id']:
            # Get user's tier limits
            limits = tier_handler.get_limits(user_id)
            
            # Check text length against limits
            if len(message.content) > limits['text_limit']:
                # Send a private notification about the limit
                try:
                    await message.author.send(
                        f"🔒 Message too long for auto-translation! Free tier limit: {limits['text_limit']} characters\n"
                        f"Use /premium to get unlimited translation!"
                    )
                except:
                    # Can't DM the user, ignore
                    pass
                return
            
            # Don't translate if the message is a command
            if message.content.startswith('/'):
                return
                
            try:
                source_code = settings['source']
                target_code = settings['target']
                
                # If source is auto, detect the language
                if source_code == "auto":
                    try:
                        detected_lang = detect(message.content)
                        source_code = detected_lang
                    except:
                        # If detection fails, default to English
                        source_code = "en"
                
                # Don't translate if source and target are the same
                if source_code == target_code:
                    return
                
                # Translate the text
                translator = GoogleTranslator(source=source_code, target=target_code)
                translated = translator.translate(message.content)
                
                # Get proper language names and flags
                source_name = languages.get(source_code, source_code)
                target_name = languages.get(target_code, target_code)
                source_flag = flag_mapping.get(source_code, '🌐')
                target_flag = flag_mapping.get(target_code, '🌐')
                
                # Create embed
                embed = discord.Embed(
                    title="Auto Translation",
                    color=0x3498db
                )
                
                # Check if user wants to hide original text
                if user_id not in hidden_sessions:
                    embed.add_field(
                        name=f"{source_flag} Original ({source_name})",
                        value=message.content,
                        inline=False
                    )
                
                embed.add_field(
                    name=f"{target_flag} Translation ({target_name})",
                    value=translated,
                    inline=False
                )
                
                # Send the translation
                await message.channel.send(embed=embed)
            except Exception as e:
                print(f"Auto-translation error: {e}")
    
    return

@tree.command(name="hide", description="Hide original speech")
async def hide_speech(interaction: discord.Interaction):
    user_id = interaction.user.id
    hidden_sessions.add(user_id)
    await interaction.response.send_message("Original speech will be hidden! 🙈", ephemeral=True)

@tree.command(name="show", description="Show original speech")
async def show_speech(interaction: discord.Interaction):
    user_id = interaction.user.id
    hidden_sessions.discard(user_id)
    await interaction.response.send_message("Original speech will be shown! 👀", ephemeral=True)

@tree.command(name="stop", description="Stop active translation")
async def stop_translation(interaction: discord.Interaction):
    user_id = interaction.user.id
    guild_id = interaction.guild_id
    
    # Track if we found and stopped any sessions
    stopped_any = False
    
    # Check for voice translation session (voicechat command)
    if guild_id in voice_translation_sessions:
        session = voice_translation_sessions[guild_id]
        
        # Stop listening if active
        if session['voice_client'].is_listening():
            session['voice_client'].stop_listening()
        
        # Clean up sink
        if 'sink' in session:
            session['sink'].cleanup()
        
        # Stop any playing audio
        if session['voice_client'].is_playing():
            session['voice_client'].stop()
        
        # Disconnect from voice
        await session['voice_client'].disconnect()
        
        # Remove session
        del voice_translation_sessions[guild_id]
        stopped_any = True
    
    # Check for any active voice client (speak command)
    if interaction.guild and interaction.guild.voice_client:
        voice_client = interaction.guild.voice_client
        
        # Stop any playing audio
        if voice_client.is_playing():
            voice_client.stop()
        
        # Disconnect if not already disconnected by the voice_translation_sessions cleanup
        if voice_client.is_connected():
            await voice_client.disconnect()
            stopped_any = True
    
    # Check for text translation session
    if (guild_id in translation_server.translators and 
        user_id in translation_server.translators[guild_id]):
        
        # Remove user from translators
        del translation_server.translators[guild_id][user_id]
        
        # Cleanup user's ngrok tunnel
        translation_server.cleanup_user(user_id)
        stopped_any = True
    
    # Check for auto-translation
    if user_id in auto_translate_users:
        del auto_translate_users[user_id]
        stopped_any = True
    
    if stopped_any:
        await interaction.response.send_message("Translation session ended! 🛑", ephemeral=True)
    else:
        await interaction.response.send_message("No active translation session found!", ephemeral=True)
@tree.command(name="dmtr", description="Translate and send a message to another user")
async def dm_translate(
    interaction: discord.Interaction,
    user: discord.Member,
    text: str,
    source_lang: str,
    target_lang: str
):
    try:
        # Get user ID
        sender_id = interaction.user.id
        
        # Convert language inputs to codes
        source_code = "auto" if source_lang.lower() == "auto" else get_language_code(source_lang)
        target_code = get_language_code(target_lang)
        
        # Validate language codes
        if source_lang.lower() != "auto" and not source_code:
            await interaction.response.send_message(
                f"❌ Invalid source language: '{source_lang}'\nUse /list to see available languages or use 'auto' for automatic detection.",
                ephemeral=True
            )
            return
            
        if not target_code:
            await interaction.response.send_message(
                f"❌ Invalid target language: '{target_lang}'\nUse /list to see available languages.",
                ephemeral=True
            )
            return
        
        # Get user's tier limits
        limits = tier_handler.get_limits(sender_id)
        
        # Check text length against limits
        if len(text) > limits['text_limit']:
            await interaction.response.send_message(
                f"🔒 Text too long! Free tier limit: {limits['text_limit']} characters\n"
                f"Use /premium to get unlimited translation!",
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Detect language if set to auto
        if source_code == "auto":
            try:
                detected_lang = detect(text)
                source_code = detected_lang
                logger.info(f"Detected language: {detected_lang}")
            except Exception as e:
                logger.error(f"Language detection error: {e}")
                source_code = "en"  # Default to English if detection fails
        
        # Skip translation if detected language matches target
        if source_code == target_code:
            translated_text = text
            detected_message = " (same as target language)"
        else:
            # Translate the text
            translator = GoogleTranslator(source=source_code, target=target_code)
            translated_text = translator.translate(text)
            detected_message = ""
        
        # Get language names and flags
        source_name = languages.get(source_code, source_code)
        target_name = languages.get(target_code, target_code)
        source_flag = flag_mapping.get(source_code, '🌐')
        target_flag = flag_mapping.get(target_code, '🌐')
        
        # Create embed for the recipient
        recipient_embed = discord.Embed(
            title=f"Message from {interaction.user.display_name}",
            color=0x3498db
        )
        
        # Add source language field
        source_field_name = f"{source_flag} Original ({source_name})"
        if source_lang.lower() == "auto":
            source_field_name += f" (Detected{detected_message})"
            
        recipient_embed.add_field(
            name=source_field_name,
            value=text,
            inline=False
        )
        
        # Add target language field
        recipient_embed.add_field(
            name=f"{target_flag} Translation ({target_name})",
            value=translated_text,
            inline=False
        )
        
        # Try to send the DM
        try:
            # Create a DM channel with the user
            dm_channel = await user.create_dm()
            
            # Send the message
            await dm_channel.send(embed=recipient_embed)
            
            # Confirm to the sender
            sender_embed = discord.Embed(
                title=f"Message sent to {user.display_name}",
                description="Your message has been translated and delivered!",
                color=0x2ecc71
            )
            
            sender_embed.add_field(
                name=f"{source_flag} Original ({source_name})",
                value=text,
                inline=False
            )
            
            sender_embed.add_field(
                name=f"{target_flag} Translation ({target_name})",
                value=translated_text,
                inline=False
            )
            
            await interaction.followup.send(embed=sender_embed, ephemeral=True)
            
        except discord.Forbidden:
            await interaction.followup.send(
                f"❌ I couldn't send a DM to {user.display_name}. They might have DMs disabled or haven't added me as a friend.",
                ephemeral=True
            )
        
    except Exception as e:
        logger.error(f"DM translation error: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"❌ An error occurred: {str(e)}",
                ephemeral=True
            )
@tree.context_menu(name="Read Message")
async def translate_message_context(interaction: discord.Interaction, message: discord.Message):
    try:
        message_to_translate = message
        
        # Check if command is used in a guild
        if not interaction.guild:
            embed = discord.Embed(
                title="❌ Server Only Command",
                description="This command can only be used if I'm invited to the server!\n"
                "🔗 Use `/invite` to get the proper invite link",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Check bot permissions
        permissions = interaction.channel.permissions_for(interaction.guild.me)
        if not permissions.read_message_history:
            embed = discord.Embed(
                title="❌ Permission Error",
                description=(
                    "I don't have permission to read message history in this channel.\n\n"
                    "**Required Permission:**\n"
                    "• Read Message History\n\n"
                    "🔗 Ask a server admin to fix my permissions"
                ),
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Create a modal for language selection
        class LanguageModal(discord.ui.Modal, title="Select Target Language"):
            target_lang = discord.ui.TextInput(
                label="Target Language Code or Name",
                placeholder="Enter language code or name (e.g., es, Spanish)...",
                max_length=20
            )

            async def on_submit(self, interaction: discord.Interaction):
                target_lang_input = self.target_lang.value.lower()
                
                # Convert language input to code
                target_lang = get_language_code(target_lang_input)
                
                # Validate target language
                if not target_lang:
                    await interaction.response.send_message(
                        f"❌ Invalid target language: '{target_lang_input}'\nUse /list to see available languages.",
                        ephemeral=True
                    )
                    return

                # Get user's tier limits
                user_id = interaction.user.id
                limits = tier_handler.get_limits(user_id)
                
                # Check message length against limits
                if len(message_to_translate.content) > limits['text_limit']:
                    await interaction.response.send_message(
                        f"🔒 Message too long! Free tier limit: {limits['text_limit']} characters\n"
                        f"Use /premium to get unlimited translation!",
                        ephemeral=True
                    )
                    return
                
                # Detect the source language
                try:
                    source_lang = detect(message_to_translate.content)
                except:
                    await interaction.response.send_message(
                        "❌ Could not detect the message language.",
                        ephemeral=True
                    )
                    return
                
                # Don't translate if source and target are the same
                if source_lang == target_lang:
                    await interaction.response.send_message(
                        "Message is already in the target language! 🎯",
                        ephemeral=True
                    )
                    return
                
                # Create translator and translate
                translator = GoogleTranslator(source=source_lang, target=target_lang)
                translated = translator.translate(message_to_translate.content)
                
                # Get proper language names and flags
                source_name = languages.get(source_lang, source_lang)
                target_name = languages.get(target_lang, target_lang)
                source_flag = flag_mapping.get(source_lang, '🌐')
                target_flag = flag_mapping.get(target_lang, '🌐')
                
                # Create embed
                embed = discord.Embed(
                    title="Message Translation",
                    color=0x3498db
                )
                
                embed.add_field(
                    name=f"{source_flag} Original ({source_name})",
                    value=message_to_translate.content,
                    inline=False
                )
                
                embed.add_field(
                    name=f"{target_flag} Translation ({target_name})",
                    value=translated,
                    inline=False
                )
                
                embed.set_footer(text=f"Message from: {message_to_translate.author.display_name}")
                
                await interaction.response.send_message(embed=embed, ephemeral=True)

        # Show the language selection modal
        await interaction.response.send_modal(LanguageModal())
        
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I don't have permission to read messages in this channel.",
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ An error occurred: {str(e)}",
            ephemeral=True
        )
@tree.command(name="read", description="Translate a message by ID")
async def translate_by_id(
    interaction: discord.Interaction,
    target_lang: str,
    message_id: str
):
    try:
        # Check if command is used in a guild
        if not interaction.guild:
            embed = discord.Embed(
                title="❌ Server Only Command",
                description="This command can only be used if I'm invited to the server!\n"
                "🔗 Use `/invite` to get the proper invite link",
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Try to get message from ID
        try:
            message_to_translate = await interaction.channel.fetch_message(int(message_id))
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid message ID! Please provide a valid message ID.",
                ephemeral=True
            )
            return
        except discord.NotFound:
            await interaction.response.send_message(
                "❌ Message not found! Make sure the ID is correct and the message is in this channel.",
                ephemeral=True
            )
            return

        # Check bot permissions
        permissions = interaction.channel.permissions_for(interaction.guild.me)
        if not permissions.read_message_history:
            embed = discord.Embed(
                title="❌ Permission Error",
                description=(
                    "I don't have permission to read message history in this channel.\n\n"
                    "**Required Permission:**\n"
                    "• Read Message History\n\n"
                    "🔗 Ask a server admin to fix my permissions"
                ),
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Get user's tier limits
        user_id = interaction.user.id
        limits = tier_handler.get_limits(user_id)
        
        # Check message length against limits
        if len(message_to_translate.content) > limits['text_limit']:
            await interaction.response.send_message(
                f"🔒 Message too long! Free tier limit: {limits['text_limit']} characters\n"
                f"Use /premium to get unlimited translation!",
                ephemeral=True
            )
            return
        
        # Convert language input to code
        target_code = get_language_code(target_lang)
        
        # Validate target language
        if not target_code:
            await interaction.response.send_message(
                f"❌ Invalid target language: '{target_lang}'\nUse /list to see available languages.",
                ephemeral=True
            )
            return
            
        # Detect the source language
        try:
            source_lang = detect(message_to_translate.content)
        except:
            await interaction.response.send_message(
                "❌ Could not detect the message language.",
                ephemeral=True
            )
            return
            
        # Don't translate if source and target are the same
        if source_lang == target_code:
            await interaction.response.send_message(
                "Message is already in the target language! 🎯",
                ephemeral=True
            )
            return
            
        # Create translator and translate
        translator = GoogleTranslator(source=source_lang, target=target_code)
        translated = translator.translate(message_to_translate.content)
        
        # Get proper language names and flags
        source_name = languages.get(source_lang, source_lang)
        target_name = languages.get(target_code, target_code)
        source_flag = flag_mapping.get(source_lang, '🌐')
        target_flag = flag_mapping.get(target_code, '🌐')
        
        # Create embed
        embed = discord.Embed(
            title="Message Translation",
            color=0x3498db
        )
        
        embed.add_field(
            name=f"{source_flag} Original ({source_name})",
            value=message_to_translate.content,
            inline=False
        )
        
        embed.add_field(
            name=f"{target_flag} Translation ({target_name})",
            value=translated,
            inline=False
        )
        
        embed.set_footer(text=f"Message from: {message_to_translate.author.display_name}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I don't have permission to read messages in this channel.",
            ephemeral=True
        )
    except Exception as e:
        await interaction.response.send_message(
            f"❌ An error occurred: {str(e)}",
            ephemeral=True
        )
        
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
    
    await interaction.response.send_message(embed=embed, ephemeral=True)  
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
