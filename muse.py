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
from database import db
from feedback_db import feedback_db
from achievement_system import achievement_db, get_rank_from_points, send_achievement_notification, ACHIEVEMENTS, RARITY_INFO


YOUR_ADMIN_ID = 1192196672437096520
YOUR_SERVER_ID = 1332522833326375022

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
# Add these functions after flag_mapping and before class TierHandler:

async def language_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    # Filter languages based on what user is typing
    current_lower = current.lower()
    
    # Search both language codes and names
    matches = []
    for code, name in languages.items():
        # Match by code or name
        if (current_lower in code.lower() or 
            current_lower in name.lower()):
            # Show both code and name in the choice
            matches.append(app_commands.Choice(name=f"{name} ({code})", value=code))
    
    # Limit to 25 choices (Discord's limit)
    return matches[:25]

async def source_language_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    current_lower = current.lower()
    matches = []
    
    # Always show auto-detect first if it matches
    if not current or "auto" in current_lower:
        matches.append(app_commands.Choice(name="🔍 Auto-detect language", value="auto"))
    
    # Then add language matches
    for code, name in languages.items():
        if (current_lower in code.lower() or 
            current_lower in name.lower()):
            matches.append(app_commands.Choice(name=f"{name} ({code})", value=code))
    
    return matches[:25]
# Update the TierHandler class in your main file
class TierHandler:
    def __init__(self):
        self.premium_users = set()
        self.tiers = {
            'free': {
                'text_limit': 150,    # 150 characters per translation
                'voice_limit': 1800   # 30 minutes per day (in seconds)
            },
            'premium': {
                'text_limit': float('inf'),  # Unlimited characters per translation
                'voice_limit': float('inf')  # Unlimited voice translation
            }
        }
    
    async def get_limits(self, user_id: int):
        """Get user limits using your existing database"""
        user = await db.get_or_create_user(user_id)
        return self.tiers['premium'] if user['is_premium'] else self.tiers['free']
    
    async def check_usage_limits(self, user_id: int, text_chars: int = 0, voice_seconds: int = 0):
        """Check if user can perform action within limits using your database"""
        user = await db.get_or_create_user(user_id)
        if user['is_premium']:
            return True, "Premium user - unlimited"
        
        limits = self.tiers['free']
        
        # Check text limit (per translation, not daily)
        if text_chars > limits['text_limit']:
            return False, f"Text too long! Free tier limit: {limits['text_limit']} characters per translation"
        
        # Check voice limit (daily) using your database structure
        if voice_seconds > 0:
            daily_usage = await db.get_daily_usage(user_id)
            if (daily_usage['voice_seconds'] + voice_seconds) > limits['voice_limit']:
                remaining_minutes = max(0, (limits['voice_limit'] - daily_usage['voice_seconds']) // 60)
                return False, f"Daily voice limit exceeded! You have {remaining_minutes} minutes remaining today"
        
        return True, "Within limits"

# Update tier_handler instance
tier_handler = TierHandler()

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
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def start(interaction: discord.Interaction):
    user_id = interaction.user.id
    guild_id = interaction.guild_id
    
    # Create or get user in database
    user = await db.get_or_create_user(user_id, interaction.user.display_name)
    is_premium = user['is_premium']
    
    if guild_id not in translation_server.translators:
        translation_server.translators[guild_id] = {}
    
    if user_id not in translation_server.translators[guild_id]:
        translation_server.translators[guild_id][user_id] = {}  # Simple dictionary instead of LiveVoiceTranslator
        translation_server.get_user_url(user_id)
        
        # Create welcome embed
        embed = discord.Embed(
            title="🎉 Welcome to Muse Translator!",
            description=f"Hello {interaction.user.display_name}! Your personal translator is ready to use.",
            color=0x2ecc71 if is_premium else 0x3498db
        )
        
        # Add tier-specific information
        if is_premium:
            embed.add_field(
                name="⭐ Premium Account Active",
                value=(
                    "• Unlimited character translation\n"
                    "• Unlimited voice translation\n"
                    "• Full translation history\n"
                    "• Priority support"
                ),
                inline=False
            )
        else:
            embed.add_field(
                name="🆓 Free Tier Limits",
                value=(
                    "• 150 characters per translation\n"
                    "• 30 minutes voice translation per day\n"
                    "• Recent translation history\n"
                    "• Use `/premium` to upgrade for unlimited access!"
                ),
                inline=False
            )
        
        # Add command categories
        embed.add_field(
            name="🗣️ Voice Commands",
            value=(
                "`/voicechat [source] [target]` - Real-time voice chat translation\n"
                "`/voicechat2 [lang1] [lang2]` - Enhanced bidirectional translation\n"
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
                "`/read [message_id] [target]` - Translate any sent message by ID\n"
                "`/dmtr [user] [text] [source] [target]` - Send translated DM"
            ),
            inline=False
        )
        
        embed.add_field(
            name="⚙️ Settings & Info",
            value=(
                "`/preferences [source] [target]` - Set default languages\n"
                "`/hide` or `/show` - Toggle original text visibility\n"
                "`/stats` - View your translation statistics\n"
                "`/history [limit]` - View recent translations\n"
                "`/stop` - End translation session"
            ),
            inline=False
        )
        
        embed.add_field(
            name="ℹ️ Information",
            value=(
                "`/list` - See all supported languages\n"
                "`/status` - Check your subscription status\n"
                "`/premium` - Unlock premium features\n"
                "`/invite` - Get the bot's invite link\n"
                "`/help` - Show detailed command help"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📝 Language Format",
            value=(
                "You can use language names or codes:\n"
                "• Names: `English`, `Spanish`, `Japanese`\n"
                "• Codes: `en`, `es`, `ja`\n"
                "• Example: `/texttr text:'Hello World' source_lang:English target_lang:Spanish`"
            ),
            inline=False
        )
        
        # Add footer with server invite
        embed.set_footer(text="Join our support server: https://discord.gg/VMpBsbhrff")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        print(f"🔥 New user connected: {interaction.user.display_name} ({'Premium' if is_premium else 'Free'})")
    else:
        # Create already running embed
        embed = discord.Embed(
            title="🚀 Translator Already Running",
            description="Your translator is already active and ready to use!",
            color=0x2ecc71 if is_premium else 0x3498db
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
        
        # Show current tier status
        if is_premium:
            embed.add_field(
                name="⭐ Premium Active",
                value="Unlimited translation access",
                inline=True
            )
        else:
            embed.add_field(
                name="🆓 Free Tier",
                value="150 chars/translation, 30 min voice/day",
                inline=True
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
# Update the texttr command to use new limits
@tree.command(name="texttr", description="Translate text between languages")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(
    text="Text to translate",
    source_lang="Source language (type to search)",
    target_lang="Target language (type to search)"
)
async def text_translate(
    interaction: discord.Interaction,
    text: str,
    source_lang: str,
    target_lang: str
):
    user_id = interaction.user.id
    
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
    
    # Check usage limits
    can_translate, limit_message = await tier_handler.check_usage_limits(user_id, text_chars=len(text))
    if not can_translate:
        await interaction.response.send_message(
            f"🔒 {limit_message}\n💡 Use `/premium` to get unlimited translation!",
            ephemeral=True
        )
        return

    # Handle both guild and user contexts for User-Installable Apps
    if interaction.guild:
        guild_id = interaction.guild_id
        if guild_id not in translation_server.translators or user_id not in translation_server.translators[guild_id]:
            await interaction.response.send_message("Please use /start first to initialize your translator! 🎯")
            return
    # If no guild (DM/user context), skip the server check
        
    try:
        translator = GoogleTranslator(source=source_code, target=target_code)
        translated = translator.translate(text)
        
        # Track usage in database
        await db.track_usage(user_id, text_chars=len(text))
        
        # Save translation to history
        await db.save_translation(
            user_id=user_id,
            guild_id=interaction.guild_id,
            original_text=text,
            translated_text=translated,
            source_lang=source_code,
            target_lang=target_code,
            translation_type="text"
        )

        # ADD THIS TRACKING LINE:
        achievement_db.track_translation(
            user_id, 
            source_code, 
            target_code, 
            user_id in tier_handler.premium_users
        )
        
        # Check for new achievements and notify
        new_achievements = achievement_db.check_achievements(user_id)
        if new_achievements:
            await send_achievement_notification(client, user_id, new_achievements)
        
        # Get proper language names and flags
        source_name = languages.get(source_code, source_code)
        target_name = languages.get(target_code, target_code)
        source_flag = flag_mapping.get(source_code, '🌐')
        target_flag = flag_mapping.get(target_code, '🌐')
        
        username = interaction.user.display_name
        
        # Get user for premium status
        user = await db.get_or_create_user(user_id, username)
        
        # Create embed with appropriate fields based on hidden status
        embed = discord.Embed(
            title="Text Translation",
            color=0x2ecc71 if user['is_premium'] else 0x3498db
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
        
        # Add context indicator and character count for free users
        if interaction.guild:
            if user['is_premium']:
                embed.set_footer(text=f"Server: {interaction.guild.name} • Premium User")
            else:
                embed.set_footer(text=f"Characters: {len(text)}/150 • Server: {interaction.guild.name} • /premium for unlimited")
        else:
            if user['is_premium']:
                embed.set_footer(text="User Mode: DM Translation • Premium User")
            else:
                embed.set_footer(text=f"Characters: {len(text)}/150 • User Mode: DM Translation • /premium for unlimited")
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Translation failed: {str(e)}\n"
            f"Please check your language codes (e.g., 'en' for English, 'es' for Spanish)"
        )

# Add autocomplete to the command
text_translate.autocomplete('source_lang')(source_language_autocomplete)
text_translate.autocomplete('target_lang')(language_autocomplete)

@tree.command(name="voice", description="Translate text and convert to speech")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(
    text="Text to translate and convert to speech",
    source_lang="Source language (type to search)",
    target_lang="Target language (type to search)"
)
async def translate_and_speak(
    interaction: discord.Interaction,
    text: str,
    source_lang: str,
    target_lang: str
):
    try:
        # Handle both contexts
        if interaction.guild:
            # Server context - existing logic
            pass
        else:
            # User context (DM) - just create audio file, no voice channel
            pass

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
        
        # Check text length against limits (per translation)
        can_translate, limit_message = await tier_handler.check_usage_limits(user_id, text_chars=len(text))
        if not can_translate:
            await interaction.response.send_message(
                f"🔒 {limit_message}\n💡 Try shorter text or use /premium for unlimited translation!",
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

        # Track usage in database
        await db.track_usage(user_id, text_chars=len(text))
        
        # Save translation to history
        await db.save_translation(
            user_id=user_id,
            guild_id=interaction.guild_id or 0,
            original_text=text,
            translated_text=translated_text,
            source_lang=source_code,
            target_lang=target_code,
            translation_type="voice"
        )

        # ADD THIS TRACKING LINE after successful translation:
        achievement_db.track_translation(
            user_id, 
            source_code, 
            target_code, 
            user_id in tier_handler.premium_users
        )
    
        # Check for achievements
        new_achievements = achievement_db.check_achievements(user_id)
        if new_achievements:
            await send_achievement_notification(client, user_id, new_achievements)

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
        
        # Add character count for free users
        user = await db.get_or_create_user(user_id)
        if not user['is_premium']:
            embed.set_footer(text=f"Characters used: {len(text)}/150 • Upgrade: /premium")
        else:
            # Add context info for premium users
            if interaction.guild:
                embed.set_footer(text=f"Server: {interaction.guild.name} • Premium User")
            else:
                embed.set_footer(text="User Context: Audio file generated • Premium User")
            
        # Send the embed as ephemeral
        await interaction.followup.send(
            embed=embed,
            ephemeral=True
        )

        # Send the audio file
        if interaction.guild:
            # In server - send to channel
            await interaction.channel.send(
                file=discord.File(mp3_fp, filename='translated_speech.mp3')
            )
        else:
            # In DM - send directly
            await interaction.followup.send(
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
# Add autocomplete
translate_and_speak.autocomplete('source_lang')(source_language_autocomplete)
translate_and_speak.autocomplete('target_lang')(language_autocomplete)

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('muse')

# Update the voice chat commands to use new limits (complete voicechat command)
@tree.command(name="voicechat", description="Translate voice chat in real-time")
@app_commands.describe(
    source_lang="Source language (type to search, or 'auto' for detection)",
    target_lang="Target language (type to search)"
)
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
        
    # Get user's tier limits and check voice usage
    user_id = interaction.user.id
    user = await db.get_or_create_user(user_id, interaction.user.display_name)
    
    # Check voice limits for free users
    if not user['is_premium']:
        daily_usage = await db.get_daily_usage(user_id)
        remaining_seconds = 1800 - daily_usage['voice_seconds']  # 30 minutes = 1800 seconds
        
        if remaining_seconds <= 0:
            embed = discord.Embed(
                title="🔒 Daily Voice Limit Reached",
                description=(
                    "You've used your 30 minutes of voice translation for today!\n\n"
                    "**Upgrade to Premium for unlimited voice translation:**\n"
                    "• Just $1/month\n"
                    "• Unlimited voice translation\n"
                    "• Unlimited text translation\n"
                    "• Full translation history\n\n"
                    "Use `/premium` to upgrade now!"
                ),
                color=0xFF6B6B
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        elif remaining_seconds < 300:  # Less than 5 minutes remaining
            embed = discord.Embed(
                title="⚠️ Voice Limit Warning",
                description=(
                    f"You have {remaining_seconds//60} minutes of voice translation remaining today.\n"
                    f"Consider upgrading to premium for unlimited access!"
                ),
                color=0xF39C12
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
    
    voice_channel = interaction.user.voice.channel
    
    # Define the TranslationSink class with usage tracking
    class TranslationSink(BasicSink):
        def __init__(self, *, source_language, target_language, text_channel, client_instance, user_id):
            # Must call super().__init__() as per documentation
            self.event = asyncio.Event()
            super().__init__(self.event)
            self.source_language = source_language
            self.target_language = target_language
            self.text_channel = text_channel
            self.client_instance = client_instance
            self.initiating_user_id = user_id
            self.user_buffers = {}
            self.processing_queue = queue.Queue()
            self.is_running = True
            self.start_time = time.time()
            self.processing_thread = threading.Thread(target=self._process_audio)
            self.processing_thread.start()
            logger.info("TranslationSink initialized with usage tracking")
            
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
                
                # Save translation to database
                await db.save_translation(
                    user_id=user_id,
                    guild_id=guild.id,
                    original_text=original_text,
                    translated_text=translated_text,
                    source_lang=source_lang,
                    target_lang=self.target_language,
                    translation_type="voice_chat"
                )
                
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
        
        async def cleanup(self):
            logger.info("Cleaning up TranslationSink")
            self.is_running = False
            
            # Calculate session duration and track usage
            session_duration = int(time.time() - self.start_time)
            await db.track_usage(self.initiating_user_id, voice_seconds=session_duration)
            logger.info(f"Voice session duration: {session_duration} seconds")
            
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
        
        # Create our custom sink with usage tracking
        logger.info("Creating TranslationSink")
        sink = TranslationSink(
            source_language=source_code,
            target_language=target_code,
            text_channel=interaction.channel,
            client_instance=client,
            user_id=user_id
        )
        logger.info("Successfully created TranslationSink")
        # ADD THIS TRACKING LINE after successful connection:
        achievement_db.track_voice_session(
            user_id, 
            user_id in tier_handler.premium_users
        )
        
        # Check for new achievements
        new_achievements = achievement_db.check_achievements(user_id)
        if new_achievements:
            await send_achievement_notification(client, user_id, new_achievements)
        
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
            is_premium = user['is_premium']
            
            # Create embed with appropriate styling
            embed = discord.Embed(
                title="🎤 Voice Chat Translation Started",
                description=(
                    f"Now translating voice chat from {source_flag} {source_display} to {target_flag} {target_display}.\n"
                    f"Speak clearly for best results.\n"
                    f"Use `/stop` to end the translation session."
                ),
                color=0x2ecc71 if is_premium else 0x3498db
            )
            
            # Add usage info for free users
            if not is_premium:
                daily_usage = await db.get_daily_usage(user_id)
                remaining_minutes = max(0, (1800 - daily_usage['voice_seconds']) // 60)
                embed.add_field(
                    name="⏱️ Usage Info",
                    value=f"Voice time remaining today: {remaining_minutes} minutes",
                    inline=False
                )
                embed.add_field(
                    name="💡 Upgrade Tip",
                    value="Get unlimited voice translation with `/premium`",
                    inline=False
                )
            else:
                embed.add_field(
                    name="⭐ Premium Active",
                    value="Unlimited voice translation time",
                    inline=False
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
                'channel': voice_channel,
                'type': 'standard',
                'user_id': user_id
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

# Add autocomplete to the command
voice_chat_translate.autocomplete('source_lang')(source_language_autocomplete)
voice_chat_translate.autocomplete('target_lang')(language_autocomplete)

@tree.command(name="voicechat2", description="Enhanced bidirectional voice chat translation between two languages")
@app_commands.describe(
    language1="First language to translate from (type to search)",
    language2="Second language to translate from (type to search)",
)
async def voice_chat_translate_bidirectional_v2(
    interaction: discord.Interaction, 
    language1: str,
    language2: str
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
    lang1_code = "auto" if language1.lower() == "auto" else get_language_code(language1)
    lang2_code = "auto" if language2.lower() == "auto" else get_language_code(language2)
    
    # Validate language codes (at least one must not be auto)
    if language1.lower() != "auto" and not lang1_code:
        await interaction.response.send_message(
            f"❌ Invalid language: '{language1}'\nUse /list to see available languages or use 'auto' for automatic detection.",
            ephemeral=True
        )
        return
        
    if language2.lower() != "auto" and not lang2_code:
        await interaction.response.send_message(
            f"❌ Invalid language: '{language2}'\nUse /list to see available languages or use 'auto' for automatic detection.",
            ephemeral=True
        )
        return
    
    # Don't allow both languages to be auto
    if lang1_code == "auto" and lang2_code == "auto":
        await interaction.response.send_message(
            "❌ At least one language must be specified (not 'auto'). Example: `/voicechat2 auto english`",
            ephemeral=True
        )
        return
        
    # Get user's tier limits
    user_id = interaction.user.id
    limits = tier_handler.get_limits(user_id)
    
    voice_channel = interaction.user.voice.channel
    
    # Define the Enhanced Bidirectional TranslationSink class for voicechat2
    class EnhancedBidirectionalTranslationSink(BasicSink):
        def __init__(self, *, language1, language2, text_channel, client_instance):
            self.event = asyncio.Event()
            super().__init__(self.event)
            self.language1 = language1  # Can be "auto"
            self.language2 = language2  # Can be "auto"
            self.text_channel = text_channel
            self.client_instance = client_instance
            self.user_buffers = {}
            self.user_detected_languages = {}  # Track detected languages per user
            self.processing_queue = queue.Queue()
            self.is_running = True
            self.error_count = 0
            self.last_successful_processing = time.time()
            self.processing_thread = threading.Thread(target=self._process_audio, daemon=True)
            self.processing_thread.start()
            logger.info("EnhancedBidirectionalTranslationSink initialized")
            
        def wants_opus(self) -> bool:
            return False
            
        def write(self, user, data):
            try:
                # Skip processing if we're getting too many errors
                if self.error_count > 50:
                    return
                    
                user_id = user.id if hasattr(user, 'id') else str(user)
                
                # Enhanced validation
                if not hasattr(data, 'pcm'):
                    return
                    
                pcm_data = data.pcm
                if not pcm_data or len(pcm_data) < 50:
                    return
                    
                # Skip silence or invalid data
                if pcm_data == b'\x00' * len(pcm_data):
                    return
                    
                # Check for reasonable PCM data size (not too big, not too small)
                if len(pcm_data) > 10000:  # Skip unusually large chunks
                    return
                    
                if user_id not in self.user_buffers:
                    self.user_buffers[user_id] = []
                    self.user_detected_languages[user_id] = None
                    logger.info(f"New user buffer created for user {user_id}")
                
                self.user_buffers[user_id].append(pcm_data)
                
                # Process audio every 3-4 seconds for more stable chunks
                if len(self.user_buffers[user_id]) >= 150:  # Increased threshold
                    logger.info(f"Processing audio buffer for user {user_id}")
                    audio_buffer = b''.join(self.user_buffers[user_id])
                    self.user_buffers[user_id] = []
                    
                    # Only process if we have substantial audio data
                    if len(audio_buffer) > 8000:  # Increased minimum size
                        self.processing_queue.put((user_id, audio_buffer))
                        self.last_successful_processing = time.time()
                        
            except Exception as e:
                self.error_count += 1
                if self.error_count % 10 == 0:  # Log every 10th error to avoid spam
                    logger.warning(f"Audio write errors: {self.error_count}")
                return
        
        def _process_audio(self):
            logger.info("Enhanced bidirectional audio processing thread started")
            consecutive_failures = 0
            
            while self.is_running:
                try:
                    # Check if we should continue processing
                    if time.time() - self.last_successful_processing > 300:  # 5 minutes
                        logger.warning("No successful audio processing in 5 minutes")
                        
                    user_id, audio_buffer = self.processing_queue.get(timeout=1.0)
                    logger.info(f"Got audio data from queue for user {user_id} ({len(audio_buffer)} bytes)")
                    
                    # Validate audio buffer
                    if len(audio_buffer) < 8000:
                        logger.debug("Audio buffer too small, skipping")
                        continue
                    
                    # Reset consecutive failures on successful queue get
                    consecutive_failures = 0
                    
                    # Create temporary file with better error handling
                    try:
                        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                            temp_filename = temp_file.name
                            
                        # Write WAV file with error handling
                        with wave.open(temp_filename, 'wb') as wf:
                            wf.setnchannels(2)
                            wf.setsampwidth(2)
                            wf.setframerate(48000)
                            wf.writeframes(audio_buffer)
                        
                        # Verify the file was created successfully
                        if os.path.getsize(temp_filename) > 1000:  # At least 1KB
                            logger.info(f"Created WAV file: {temp_filename} ({os.path.getsize(temp_filename)} bytes)")
                            
                            # Process in separate thread with timeout
                            processing_thread = threading.Thread(
                                target=self._transcribe_and_translate_enhanced,
                                args=(temp_filename, user_id),
                                daemon=True
                            )
                            processing_thread.start()
                        else:
                            logger.warning("WAV file too small, skipping")
                            try:
                                os.unlink(temp_filename)
                            except:
                                pass
                                
                    except Exception as file_error:
                        logger.error(f"Error creating audio file: {file_error}")
                        try:
                            os.unlink(temp_filename)
                        except:
                            pass
                            
                except queue.Empty:
                    # Normal timeout, continue
                    continue
                except Exception as e:
                    consecutive_failures += 1
                    logger.error(f"Error in audio processing loop (consecutive: {consecutive_failures}): {e}")
                    
                    # If too many consecutive failures, take a break
                    if consecutive_failures > 10:
                        logger.error("Too many consecutive failures, pausing audio processing")
                        time.sleep(5)
                        consecutive_failures = 0
        
        def _determine_target_language_enhanced(self, detected_lang, user_id):
            """Enhanced target language determination with strict language pair logic"""
            
            # If both languages are specified (not auto), use strict bidirectional logic
            if self.language1 != "auto" and self.language2 != "auto":
                # If detected language matches language1, translate to language2
                if detected_lang == self.language1:
                    logger.info(f"Detected {detected_lang} matches language1 ({self.language1}), translating to language2 ({self.language2})")
                    return self.language2
                # If detected language matches language2, translate to language1
                elif detected_lang == self.language2:
                    logger.info(f"Detected {detected_lang} matches language2 ({self.language2}), translating to language1 ({self.language1})")
                    return self.language1
                else:
                    # If detected language doesn't match either specified language,
                    # assume it's closest to language1 and translate to language2
                    logger.info(f"Detected {detected_lang} doesn't match either specified language, defaulting to translate to language2 ({self.language2})")
                    return self.language2
            
            # If language1 is auto, translate to language2
            elif self.language1 == "auto" and self.language2 != "auto":
                logger.info(f"Language1 is auto, translating detected {detected_lang} to language2 ({self.language2})")
                return self.language2
            
            # If language2 is auto, translate to language1
            elif self.language2 == "auto" and self.language1 != "auto":
                logger.info(f"Language2 is auto, translating detected {detected_lang} to language1 ({self.language1})")
                return self.language1
            
            # Fallback (shouldn't happen due to validation)
            logger.warning("Unexpected language configuration, defaulting to English")
            return "en"
        
        async def _send_translation(self, user_id, original_text, translated_text, detected_lang, target_lang):
            try:
                # Check permissions first
                permissions = self.text_channel.permissions_for(self.text_channel.guild.me)
                if not permissions.send_messages or not permissions.embed_links:
                    logger.error("Missing permissions to send messages or embed links")
                    return
                
                guild = self.text_channel.guild
                try:
                    member = await guild.fetch_member(user_id)
                except discord.NotFound:
                    logger.error(f"Member {user_id} not found in guild")
                    return
                
                if not member:
                    return
                    
                username = member.display_name
                logger.info(f"Sending enhanced translation for user {username}")
                
                # Get language names and flags
                source_name = languages.get(detected_lang, detected_lang)
                target_name = languages.get(target_lang, target_lang)
                source_flag = flag_mapping.get(detected_lang, '🌐')
                target_flag = flag_mapping.get(target_lang, '🌐')
                
                # Create embed with enhanced styling
                embed = discord.Embed(
                    title=f"🚀 Enhanced Voice Translation: {username}",
                    color=0x9b59b6  # Purple color to distinguish from other versions
                )
                
                if user_id not in hidden_sessions:
                    embed.add_field(
                        name=f"{source_flag} Detected ({source_name})",
                        value=original_text[:1024],
                        inline=False
                    )
                
                embed.add_field(
                    name=f"{target_flag} Translation ({target_name})",
                    value=translated_text[:1024],
                    inline=False
                )
                
                # Add language pair info in footer
                lang1_display = "Auto-detect" if self.language1 == "auto" else languages.get(self.language1, self.language1)
                lang2_display = "Auto-detect" if self.language2 == "auto" else languages.get(self.language2, self.language2)
                embed.set_footer(text=f"Enhanced V2 | Language pair: {lang1_display} ↔ {lang2_display}")
                
                await self.text_channel.send(embed=embed)
                logger.info("Enhanced translation sent successfully")
                
            except discord.Forbidden as e:
                logger.error(f"Permission error sending translation: {e}")
            except discord.HTTPException as e:
                logger.error(f"HTTP error sending translation: {e}")
            except Exception as e:
                logger.error(f"Unexpected error sending translation: {e}")
        
        def _transcribe_and_translate_enhanced(self, filename, user_id):
            try:
                logger.info(f"Enhanced transcription for user {user_id}")
                
                recognizer = sr.Recognizer()
                recognizer.energy_threshold = 300
                recognizer.dynamic_energy_threshold = True
                
                with sr.AudioFile(filename) as source:
                    recognizer.adjust_for_ambient_noise(source, duration=0.5)
                    audio = recognizer.record(source)
                    
                    try:
                        # Enhanced speech recognition with language prioritization
                        text = None
                        detected_lang = None
                        
                        # If we have specific languages (not auto), try them in order
                        if self.language1 != "auto" and self.language2 != "auto":
                            # Try language1 first
                            try:
                                text = recognizer.recognize_google(audio, language=self.language1)
                                detected_lang = self.language1
                                logger.info(f"Successfully recognized as {self.language1}: {text}")
                            except sr.UnknownValueError:
                                # Try language2 if language1 failed
                                try:
                                    text = recognizer.recognize_google(audio, language=self.language2)
                                    detected_lang = self.language2
                                    logger.info(f"Successfully recognized as {self.language2}: {text}")
                                except sr.UnknownValueError:
                                    # If both specific languages fail, try auto-detection as fallback
                                    try:
                                        text = recognizer.recognize_google(audio)
                                        detected_lang = detect(text)
                                        logger.info(f"Fallback auto-detection: {detected_lang} - {text}")
                                    except:
                                        logger.info("Could not recognize speech in any language")
                                        return
                        
                        # If one language is auto, use the other as primary
                        elif self.language1 == "auto":
                            try:
                                text = recognizer.recognize_google(audio, language=self.language2)
                                detected_lang = self.language2
                                logger.info(f"Recognized as specified language {self.language2}: {text}")
                            except sr.UnknownValueError:
                                try:
                                    text = recognizer.recognize_google(audio)
                                    detected_lang = detect(text)
                                    logger.info(f"Auto-detection fallback: {detected_lang} - {text}")
                                except:
                                    return
                                    
                        elif self.language2 == "auto":
                            try:
                                text = recognizer.recognize_google(audio, language=self.language1)
                                detected_lang = self.language1
                                logger.info(f"Recognized as specified language {self.language1}: {text}")
                            except sr.UnknownValueError:
                                try:
                                    text = recognizer.recognize_google(audio)
                                    detected_lang = detect(text)
                                    logger.info(f"Auto-detection fallback: {detected_lang} - {text}")
                                except:
                                    return
                        
                        if not text or len(text.strip()) < 2:
                            return
                        
                        # Store detected language for this user
                        self.user_detected_languages[user_id] = detected_lang
                        
                        # Determine target language using enhanced logic
                        target_lang = self._determine_target_language_enhanced(detected_lang, user_id)
                        logger.info(f"Target language determined: {target_lang}")
                        
                        # Skip if same language
                        if detected_lang == target_lang:
                            logger.info("Source and target languages are the same, skipping translation")
                            return
                        
                        # Translate with enhanced error handling
                        try:
                            translator = GoogleTranslator(source=detected_lang, target=target_lang)
                            translated = translator.translate(text)
                            logger.info(f"Translated text: {translated}")
                            
                            if translated and len(translated.strip()) > 0:
                                asyncio.run_coroutine_threadsafe(
                                    self._send_translation(user_id, text, translated, detected_lang, target_lang),
                                    self.client_instance.loop
                                )
                            
                        except Exception as translate_error:
                            logger.error(f"Translation error: {translate_error}")
                            
                    except sr.RequestError as e:
                        logger.error(f"Speech recognition service error: {e}")
                    except Exception as recognition_error:
                        logger.error(f"Speech recognition error: {recognition_error}")
            
            except Exception as e:
                logger.error(f"Error in enhanced transcription process: {e}")
            finally:
                try:
                    if os.path.exists(filename):
                        os.unlink(filename)
                except Exception as cleanup_error:
                    logger.debug(f"Error cleaning up temp file: {cleanup_error}")
        
        def cleanup(self):
            logger.info("Cleaning up EnhancedBidirectionalTranslationSink")
            self.is_running = False
            
            # Give the processing thread time to finish
            if hasattr(self, 'processing_thread') and self.processing_thread.is_alive():
                self.processing_thread.join(timeout=3.0)
                
            # Clear any remaining buffers
            self.user_buffers.clear()
            self.user_detected_languages.clear()
            
            # Clear the processing queue
            while not self.processing_queue.empty():
                try:
                    self.processing_queue.get_nowait()
                except:
                    break
                    
        # Add sink event listeners
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
        
        # Check if we're already connected to a voice channel in this guild
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
        
        # Create our enhanced sink
        logger.info("Creating EnhancedBidirectionalTranslationSink")
        sink = EnhancedBidirectionalTranslationSink(
            language1=lang1_code,
            language2=lang2_code,
            text_channel=interaction.channel,
            client_instance=client
        )
        logger.info("Successfully created EnhancedBidirectionalTranslationSink")
        
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
            
            # Create display names for the embed
            lang1_display = "Auto-detect" if lang1_code == "auto" else languages.get(lang1_code, lang1_code)
            lang2_display = "Auto-detect" if lang2_code == "auto" else languages.get(lang2_code, lang2_code)
            lang1_flag = '🔍' if lang1_code == "auto" else flag_mapping.get(lang1_code, '🌐')
            lang2_flag = '🔍' if lang2_code == "auto" else flag_mapping.get(lang2_code, '🌐')
            
            # Check if user is premium
            is_premium = user_id in tier_handler.premium_users
            
            # Create embed with enhanced styling
            embed = discord.Embed(
                title="🚀 Enhanced Voice Chat Translation V2 Started",
                description=(
                    f"Now translating between {lang1_flag} **{lang1_display}** ↔ {lang2_flag} **{lang2_display}**\n\n"
                    f"🎯 **Enhanced Features:**\n"
                    f"• Prioritizes your specified languages\n"
                    f"• Intelligent language detection\n"
                    f"• Better audio processing\n"
                    f"• Reduced false detections\n"
                    f"• Multiple people can speak different languages!\n\n"
                    f"Use `/stop` to end the translation session."
                ),
                color=0x9b59b6  # Purple for enhanced V2
            )
            
            # Add examples based on the language pair
            if lang1_code != "auto" and lang2_code != "auto":
                embed.add_field(
                    name="📝 How it works",
                    value=(
                        f"• Speak in {lang1_display} → Translates to {lang2_display}\n"
                        f"• Speak in {lang2_display} → Translates to {lang1_display}\n"
                        f"• Other languages → Translates to {lang2_display} (default)"
                    ),
                    inline=False
                )
            elif lang1_code == "auto":
                embed.add_field(
                    name="📝 How it works",
                    value=f"• Speak in any language → Translates to {lang2_display}",
                    inline=False
                )
            else:  # lang2_code == "auto"
                embed.add_field(
                    name="📝 How it works", 
                    value=f"• Speak in any language → Translates to {lang1_display}",
                    inline=False
                )
            
            # Add tier information
            if is_premium:
                embed.add_field(
                    name="⭐ Premium Active",
                    value="Unlimited translation time",
                    inline=True
                )
            else:
                embed.add_field(
                    name="🆓 Free Tier",
                    value="30 minutes daily limit",
                    inline=True
                )
            
            # Add version info
            embed.add_field(
                name="🔧 Version",
                value="Enhanced V2",
                inline=True
            )
            
            embed.set_footer(text="Bot will automatically leave when everyone exits the voice channel")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Store the voice client and sink for later cleanup
            if interaction.guild_id not in voice_translation_sessions:
                voice_translation_sessions[interaction.guild_id] = {}
                
            voice_translation_sessions[interaction.guild_id] = {
                'voice_client': voice_client,
                'sink': sink,
                'channel': voice_channel,
                'type': 'enhanced_v2',  # Mark as enhanced V2
                'languages': [lang1_code, lang2_code]
            }
            
            # Start a task to check if users leave the voice channel
            client.loop.create_task(check_voice_channel_enhanced(voice_client, voice_channel))
                
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
voice_chat_translate_bidirectional_v2.autocomplete('language1')(source_language_autocomplete)
voice_chat_translate_bidirectional_v2.autocomplete('language2')(source_language_autocomplete)

# Enhanced voice channel checking function
async def check_voice_channel_enhanced(voice_client, voice_channel):
    """Enhanced voice channel monitoring with better error handling"""
    if not voice_client:
        return
        
    consecutive_empty_checks = 0
    error_count = 0
    
    while voice_client.is_connected():
        try:
            # Refresh the voice channel object to get current members
            updated_channel = voice_client.guild.get_channel(voice_channel.id)
            if not updated_channel:
                logger.warning("Voice channel no longer exists, disconnecting")
                break
                
            # Count human members (excluding bots)
            human_members = [member for member in updated_channel.members if not member.bot]
            member_count = len(human_members)
            
            if member_count == 0:
                consecutive_empty_checks += 1
                # Wait longer before disconnecting to avoid false positives
                if consecutive_empty_checks >= 4:  # 20 seconds of being alone
                    logger.info(f"🔇 Enhanced V2 disconnecting from {voice_channel.name} - everyone left")
                    await voice_client.disconnect()
                    break
            else:
                consecutive_empty_checks = 0  # Reset counter when people are present
                error_count = 0  # Reset error counter on successful check
            
            # Check every 5 seconds
            await asyncio.sleep(5)
            
        except Exception as e:
            error_count += 1
            logger.error(f"Error in enhanced voice channel check (count: {error_count}): {e}")
            
            # If too many errors, disconnect to prevent hanging
            if error_count > 5:
                logger.error("Too many voice channel check errors, disconnecting")
                try:
                    await voice_client.disconnect()
                except:
                    pass
                break
                
            await asyncio.sleep(5)
           
@tree.command(name="speak", description="Translate text and play speech in voice channel")
@app_commands.describe(
    text="Text to translate and play in voice channel",
    source_lang="Source language (type to search)",
    target_lang="Target language (type to search)"
)
async def translate_and_speak_voice(
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

        # Get user's tier limits and check usage
        user_id = interaction.user.id
        can_translate, limit_message = await tier_handler.check_usage_limits(user_id, text_chars=len(text))
        if not can_translate:
            await interaction.response.send_message(
                f"🔒 {limit_message}\n💡 Try shorter text or use /premium for unlimited translation!",
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

        # Track usage in database
        await db.track_usage(user_id, text_chars=len(text))
        
        # Save translation to history
        await db.save_translation(
            user_id=user_id,
            guild_id=interaction.guild_id,
            original_text=text,
            translated_text=translated_text,
            source_lang=source_code,
            target_lang=target_code,
            translation_type="speak"
        )

        # ADD THIS TRACKING LINE after successful translation:
        achievement_db.track_translation(
            user_id, 
            source_code, 
            target_code, 
            user_id in tier_handler.premium_users
        )
    
        # Check for achievements
        new_achievements = achievement_db.check_achievements(user_id)
        if new_achievements:
            await send_achievement_notification(client, user_id, new_achievements)

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
        
        # Add character count for free users
        user = await db.get_or_create_user(user_id)
        if not user['is_premium']:
            embed.set_footer(text=f"Characters: {len(text)}/150 • Server: {interaction.guild.name} • /premium for unlimited")
        else:
            embed.set_footer(text=f"Server: {interaction.guild.name} • Premium User")
            
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
                
                # Create FFmpeg audio source
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

# Add autocomplete to speak command
translate_and_speak_voice.autocomplete('source_lang')(source_language_autocomplete)
translate_and_speak_voice.autocomplete('target_lang')(language_autocomplete)


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

# Autocomplete functions for autotranslate (add these after the language dictionaries)
async def language_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    # Filter languages based on what user is typing
    current_lower = current.lower()
    
    # Search both language codes and names
    matches = []
    for code, name in languages.items():
        # Match by code or name
        if (current_lower in code.lower() or 
            current_lower in name.lower()):
            # Show both code and name in the choice
            matches.append(app_commands.Choice(name=f"{name} ({code})", value=code))
    
    # Limit to 25 choices (Discord's limit)
    return matches[:25]

async def source_language_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    current_lower = current.lower()
    matches = []
    
    # Always show auto-detect first if it matches
    if not current or "auto" in current_lower:
        matches.append(app_commands.Choice(name="🔍 Auto-detect language", value="auto"))
    
    # Then add language matches
    for code, name in languages.items():
        if (current_lower in code.lower() or 
            current_lower in name.lower()):
            matches.append(app_commands.Choice(name=f"{name} ({code})", value=code))
    
    return matches[:25]

@tree.command(name="hide", description="Hide original speech")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def hide_speech(interaction: discord.Interaction):
    user_id = interaction.user.id
    hidden_sessions.add(user_id)
    await interaction.response.send_message("Original speech will be hidden! 🙈", ephemeral=True)

@tree.command(name="show", description="Show original speech")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def show_speech(interaction: discord.Interaction):
    user_id = interaction.user.id
    hidden_sessions.discard(user_id)
    await interaction.response.send_message("Original speech will be shown! 👀", ephemeral=True)

# Update the stop command to handle cleanup properly
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
        
        # Clean up sink with usage tracking
        if 'sink' in session:
            await session['sink'].cleanup()
        
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
        embed = discord.Embed(
            title="🛑 Translation Session Ended",
            description="All active translation sessions have been stopped.",
            color=0x95a5a6
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        embed = discord.Embed(
            title="ℹ️ No Active Sessions",
            description="No active translation sessions found to stop.",
            color=0x95a5a6
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

# Update the auto_translate command to use the new limits
@tree.command(name="autotranslate", description="Automatically translate all your messages")
@app_commands.describe(
    source_lang="Source language (type to search, or 'auto' for detection)",
    target_lang="Target language (type to search)"
)
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
    
    # Check if user is premium for the warning
    user = await db.get_or_create_user(user_id, interaction.user.display_name)
    limit_warning = "" if user['is_premium'] else "\n⚠️ **Free users:** Messages over 150 characters will be skipped. Upgrade to premium for unlimited!"
    
    await interaction.response.send_message(
        f"✅ Auto-translation enabled!\n"
        f"All your messages will be translated from {source_flag} {source_display} to {target_flag} {target_display}.\n"
        f"Use `/stop` to disable auto-translation.{limit_warning}",
        ephemeral=True
    )

# Update the on_message event to use the new limits
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
            # Check usage limits (per translation)
            can_translate, limit_message = await tier_handler.check_usage_limits(user_id, text_chars=len(message.content))
            if not can_translate:
                # Send a private notification about the limit (only once per day to avoid spam)
                try:
                    # Check if we already notified today
                    daily_usage = await db.get_daily_usage(user_id)
                    if daily_usage['translations'] == 0:  # First translation attempt today
                        await message.author.send(
                            f"🔒 Auto-translation paused: {limit_message}\n"
                            f"💡 Try shorter messages or use /premium for unlimited translation!"
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
                
                # Track usage in database
                await db.track_usage(user_id, text_chars=len(message.content))
                
                # Save translation to history
                await db.save_translation(
                    user_id=user_id,
                    guild_id=message.guild.id,
                    original_text=message.content,
                    translated_text=translated,
                    source_lang=source_code,
                    target_lang=target_code,
                    translation_type="auto"
                )

                # ADD THIS TRACKING LINE:
                achievement_db.track_translation(
                    user_id, 
                    source_code, 
                    target_code, 
                    user_id in tier_handler.premium_users
                )
            
                # Check for achievements (but don't send notifications in public channels)
                achievement_db.check_achievements(user_id)
                
                
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
                
                # Add character count for free users
                user = await db.get_or_create_user(user_id)
                if not user['is_premium']:
                    embed.set_footer(text=f"Characters: {len(message.content)}/150 • Auto-translate • /premium for unlimited")
                else:
                    embed.set_footer(text="Auto-translate • Premium User")
                
                # Send the translation
                await message.channel.send(embed=embed)
            except Exception as e:
                print(f"Auto-translation error: {e}")
    
    return

# Update the dmtr command to use new limits
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
        
        # Check usage limits (per translation)
        can_translate, limit_message = await tier_handler.check_usage_limits(sender_id, text_chars=len(text))
        if not can_translate:
            await interaction.response.send_message(
                f"🔒 {limit_message}\n💡 Try shorter text or use /premium for unlimited translation!",
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
        
        # Track usage in database
        await db.track_usage(sender_id, text_chars=len(text))
        
        # Save translation to history
        await db.save_translation(
            user_id=sender_id,
            guild_id=interaction.guild_id or 0,
            original_text=text,
            translated_text=translated_text,
            source_lang=source_code,
            target_lang=target_code,
            translation_type="dm"
        )
        
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
            
            # Add character count for free users
            sender_user = await db.get_or_create_user(sender_id)
            if not sender_user['is_premium']:
                sender_embed.set_footer(text=f"Characters used: {len(text)}/150 • /premium for unlimited")
            
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

# Add autocomplete to dmtr command
dm_translate.autocomplete('source_lang')(source_language_autocomplete)
dm_translate.autocomplete('target_lang')(language_autocomplete)

@tree.command(name="read", description="Translate a message by ID")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(
    message_id="The ID of the message you want to translate (right-click message → Copy Message ID)",
    target_lang="Target language to translate to (type to search)"
)
async def translate_by_id(
    interaction: discord.Interaction,
    message_id: str,
    target_lang: str
):
    try:
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
        except discord.Forbidden:
            await interaction.response.send_message(
                "❌ I don't have permission to read messages in this channel.",
                ephemeral=True
            )
            return

        # Check if message has content to translate
        if not message_to_translate.content or not message_to_translate.content.strip():
            await interaction.response.send_message(
                "❌ This message has no text content to translate!",
                ephemeral=True
            )
            return

        # Check bot permissions (only for guild channels)
        if interaction.guild:
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

        # Get user's tier limits and check usage
        user_id = interaction.user.id
        can_translate, limit_message = await tier_handler.check_usage_limits(user_id, text_chars=len(message_to_translate.content))
        if not can_translate:
            await interaction.response.send_message(
                f"🔒 {limit_message}\n💡 Try a shorter message or use /premium for unlimited translation!",
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
                "❌ Could not detect the message language. The text might be too short or contain unsupported characters.",
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
        try:
            translator = GoogleTranslator(source=source_lang, target=target_code)
            translated = translator.translate(message_to_translate.content)
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Translation failed: {str(e)}\nPlease try again or contact support.",
                ephemeral=True
            )
            return
        
        # Track usage in database
        await db.track_usage(user_id, text_chars=len(message_to_translate.content))
        
        # Save translation to history
        await db.save_translation(
            user_id=user_id,
            guild_id=interaction.guild_id or 0,
            original_text=message_to_translate.content,
            translated_text=translated,
            source_lang=source_lang,
            target_lang=target_code,
            translation_type="read"
        )
        
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
        
        # Add character count for free users
        user = await db.get_or_create_user(user_id)
        if not user['is_premium']:
            footer_text = f"Characters: {len(message_to_translate.content)}/150 • From: {message_to_translate.author.display_name} • /premium for unlimited"
        else:
            footer_text = f"From: {message_to_translate.author.display_name} • Premium User"
        
        # Add context-appropriate footer
        if interaction.guild:
            embed.set_footer(text=footer_text)
        else:
            embed.set_footer(text=f"📱 DM Translation • {footer_text}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Read command error: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message(
                f"❌ An unexpected error occurred: {str(e)}",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"❌ An unexpected error occurred: {str(e)}",
                ephemeral=True
            )
# Add autocomplete to the read command
translate_by_id.autocomplete('target_lang')(language_autocomplete)

@tree.context_menu(name="Read Message")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def translate_message_context(interaction: discord.Interaction, message: discord.Message):
    try:
        # Check if message has content to translate
        if not message.content or not message.content.strip():
            await interaction.response.send_message(
                "❌ This message has no text content to translate!",
                ephemeral=True
            )
            return

        # Check bot permissions (only for guild channels)
        if interaction.guild:
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

        # Get user's tier limits and check usage
        user_id = interaction.user.id
        can_translate, limit_message = await tier_handler.check_usage_limits(user_id, text_chars=len(message.content))
        if not can_translate:
            await interaction.response.send_message(
                f"🔒 {limit_message}\n💡 Try a shorter message or use /premium for unlimited translation!",
                ephemeral=True
            )
            return

        # Create a modal for language selection
        class LanguageModal(discord.ui.Modal, title="Select Target Language"):
            target_lang = discord.ui.TextInput(
                label="Target Language Code or Name",
                placeholder="Enter language code or name (e.g., es, Spanish, français)...",
                max_length=30,
                required=True
            )

            def __init__(self, message_to_translate):
                super().__init__()
                self.message_to_translate = message_to_translate

            async def on_submit(self, modal_interaction: discord.Interaction):
                target_lang_input = self.target_lang.value.strip()
                
                # Convert language input to code
                target_code = get_language_code(target_lang_input)
                
                # Validate target language
                if not target_code:
                    await modal_interaction.response.send_message(
                        f"❌ Invalid target language: '{target_lang_input}'\nUse /list to see available languages.",
                        ephemeral=True
                    )
                    return
                
                # Detect the source language
                try:
                    source_lang = detect(self.message_to_translate.content)
                except:
                    await modal_interaction.response.send_message(
                        "❌ Could not detect the message language. The text might be too short or contain unsupported characters.",
                        ephemeral=True
                    )
                    return
                
                # Don't translate if source and target are the same
                if source_lang == target_code:
                    await modal_interaction.response.send_message(
                        "Message is already in the target language! 🎯",
                        ephemeral=True
                    )
                    return
                
                # Create translator and translate
                try:
                    translator = GoogleTranslator(source=source_lang, target=target_code)
                    translated = translator.translate(self.message_to_translate.content)
                except Exception as e:
                    await modal_interaction.response.send_message(
                        f"❌ Translation failed: {str(e)}\nPlease try again or contact support.",
                        ephemeral=True
                    )
                    return
                
                # Track usage in database
                await db.track_usage(modal_interaction.user.id, text_chars=len(self.message_to_translate.content))
                
                # Save translation to history
                await db.save_translation(
                    user_id=modal_interaction.user.id,
                    guild_id=modal_interaction.guild_id or 0,
                    original_text=self.message_to_translate.content,
                    translated_text=translated,
                    source_lang=source_lang,
                    target_lang=target_code,
                    translation_type="context_menu"
                )
                
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
                    value=self.message_to_translate.content,
                    inline=False
                )
                
                embed.add_field(
                    name=f"{target_flag} Translation ({target_name})",
                    value=translated,
                    inline=False
                )
                
                # Add character count for free users
                user = await db.get_or_create_user(modal_interaction.user.id)
                if not user['is_premium']:
                    footer_text = f"Characters: {len(self.message_to_translate.content)}/150 • From: {self.message_to_translate.author.display_name} • /premium for unlimited"
                else:
                    footer_text = f"From: {self.message_to_translate.author.display_name} • Premium User"
                
                # Add context-appropriate footer
                if modal_interaction.guild:
                    embed.set_footer(text=footer_text)
                else:
                    embed.set_footer(text=f"📱 DM Translation • {footer_text}")
                
                await modal_interaction.response.send_message(embed=embed, ephemeral=True)

            async def on_error(self, modal_interaction: discord.Interaction, error: Exception):
                logger.error(f"Context menu modal error: {error}")
                await modal_interaction.response.send_message(
                    "❌ An error occurred while processing your request. Please try again.",
                    ephemeral=True
                )

        # Show the language selection modal
        await interaction.response.send_modal(LanguageModal(message))
        
    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I don't have permission to read messages in this channel.",
            ephemeral=True
        )
    except Exception as e:
        logger.error(f"Context menu error: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message(
                f"❌ An unexpected error occurred: {str(e)}",
                ephemeral=True
            )


# Add autocomplete to the read command
translate_by_id.autocomplete('target_lang')(language_autocomplete)
@tree.command(name="achievements", description="View your achievements and progress")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def achievements_command(interaction: discord.Interaction):
    try:
        user_id = interaction.user.id
        stats = achievement_db.get_user_stats(user_id)
        achievements = achievement_db.get_user_achievements(user_id)
        
        if not stats:
            await interaction.response.send_message(
                "❌ No data found. Use some translation commands first!",
                ephemeral=True
            )
            return
        
        # Get user rank
        rank_info = get_rank_from_points(stats.get('total_points', 0))
        
        # Create main embed
        embed = discord.Embed(
            title=f"🏆 {interaction.user.display_name}'s Achievements",
            color=rank_info['color']
        )
        
        # Add rank and points
        embed.add_field(
            name="📊 Rank & Points",
            value=f"{rank_info['name']}\n**{stats.get('total_points', 0)}** total points",
            inline=True
        )
        
        # Add achievement count
        embed.add_field(
            name="🎯 Achievements",
            value=f"**{len(achievements)}** / **{len(ACHIEVEMENTS)}** unlocked",
            inline=True
        )
        
        # Add stats summary
        embed.add_field(
            name="📈 Statistics",
            value=(
                f"**{stats.get('total_translations', 0)}** translations\n"
                f"**{stats.get('voice_sessions', 0)}** voice sessions\n"
                f"**{stats.get('unique_languages', 0)}** languages used"
            ),
            inline=True
        )
        
        # Show recent achievements (last 5)
        if achievements:
            recent_achievements = achievements[:5]
            achievement_text = ""
            
            for ach in recent_achievements:
                rarity_info = RARITY_INFO.get(ach['rarity'], {})
                achievement_text += f"{rarity_info.get('emoji', '⚪')} **{ach['name']}** (+{ach['points']} pts)\n"
            
            embed.add_field(
                name="🎉 Recent Achievements",
                value=achievement_text,
                inline=False
            )
        else:
            embed.add_field(
                name="🎯 Get Started",
                value="Use `/texttr` or `/voicechat` to start earning achievements!",
                inline=False
            )
        
        # Add context info
        if interaction.guild:
            embed.set_footer(text=f"Server: {interaction.guild.name}")
        else:
            embed.set_footer(text="🏆 Achievement System")
        
        # Create view with buttons
        view = AchievementView(user_id)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Achievements command error: {e}")
        await interaction.response.send_message(
            "❌ An error occurred while fetching your achievements.",
            ephemeral=True
        )

class AchievementView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=300)
        self.user_id = user_id
    
    @discord.ui.button(label="📋 All Achievements", style=discord.ButtonStyle.primary)
    async def all_achievements(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            achievements = achievement_db.get_user_achievements(self.user_id)
            earned_ids = [ach['id'] for ach in achievements]
            
            embed = discord.Embed(
                title="📋 All Achievements",
                description="Your achievement collection:",
                color=0x3498db
            )
            
            # Group by category
            categories = {}
            for ach_id, ach_data in ACHIEVEMENTS.items():
                category = ach_data['category']
                if category not in categories:
                    categories[category] = []
                
                rarity_info = RARITY_INFO.get(ach_data['rarity'], {})
                status = "✅" if ach_id in earned_ids else "❌"
                
                categories[category].append(
                    f"{status} {rarity_info.get('emoji', '⚪')} **{ach_data['name']}** ({ach_data['points']} pts)\n"
                    f"    {ach_data['description']}"
                )
            
            # Add fields for each category
            for category, ach_list in categories.items():
                embed.add_field(
                    name=f"📂 {category}",
                    value="\n".join(ach_list),
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"All achievements error: {e}")
            await interaction.response.send_message("❌ Error loading achievements.", ephemeral=True)
    
    @discord.ui.button(label="🎯 Progress", style=discord.ButtonStyle.secondary)
    async def progress(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            stats = achievement_db.get_user_stats(self.user_id)
            achievements = achievement_db.get_user_achievements(self.user_id)
            earned_ids = [ach['id'] for ach in achievements]
            
            embed = discord.Embed(
                title="🎯 Achievement Progress",
                description="Your progress towards achievements:",
                color=0x2ecc71
            )
            
            # Show progress for unearned achievements
            progress_text = ""
            for ach_id, ach_data in ACHIEVEMENTS.items():
                if ach_id in earned_ids:
                    continue
                
                stat_type = ach_data['stat']
                requirement = ach_data['requirement']
                current = 0
                
                if stat_type == 'translations':
                    current = stats.get('total_translations', 0)
                elif stat_type == 'voice_sessions':
                    current = stats.get('voice_sessions', 0)
                elif stat_type == 'unique_languages':
                    current = stats.get('unique_languages', 0)
                elif stat_type == 'premium':
                    current = "Premium Required" if not stats.get('is_premium', False) else "✅"
                elif stat_type == 'early_user':
                    current = "Early User Status" if not stats.get('is_early_user', False) else "✅"
                
                if isinstance(current, int) and isinstance(requirement, int):
                    progress_bar = "█" * min(10, int((current / requirement) * 10))
                    progress_bar += "░" * (10 - len(progress_bar))
                    progress_text += f"**{ach_data['name']}**\n{progress_bar} {current}/{requirement}\n\n"
                else:
                    progress_text += f"**{ach_data['name']}**\n{current}\n\n"
            
            if progress_text:
                embed.description = progress_text
            else:
                embed.description = "🎉 All achievements unlocked! You're amazing!"
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Progress error: {e}")
            await interaction.response.send_message("❌ Error loading progress.", ephemeral=True)
    
    @discord.ui.button(label="📊 Leaderboard", style=discord.ButtonStyle.success)
    async def leaderboard(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Get top 10 users by points
            import sqlite3
            with sqlite3.connect(achievement_db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, total_points, total_translations, voice_sessions 
                    FROM user_stats 
                    ORDER BY total_points DESC 
                    LIMIT 10
                ''')
                top_users = cursor.fetchall()
            
            embed = discord.Embed(
                title="🏆 Achievement Leaderboard",
                description="Top users by achievement points:",
                color=0xf1c40f
            )
            
            leaderboard_text = ""
            for i, (user_id, points, translations, voice_sessions) in enumerate(top_users, 1):
                try:
                    user = await client.fetch_user(user_id)
                    username = user.display_name if user else f"User {user_id}"
                except:
                    username = f"User {user_id}"
                
                rank_info = get_rank_from_points(points)
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                
                leaderboard_text += f"{medal} **{username}** - {points} pts ({rank_info['name']})\n"
            
            embed.description = leaderboard_text if leaderboard_text else "No users found."
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Leaderboard error: {e}")
            await interaction.response.send_message("❌ Error loading leaderboard.", ephemeral=True)

@tree.command(name="mystats", description="View your detailed statistics and achievements")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def my_stats(interaction: discord.Interaction):
    try:
        user_id = interaction.user.id
        stats = achievement_db.get_user_stats(user_id)
        achievements = achievement_db.get_user_achievements(user_id)
        
        if not stats:
            await interaction.response.send_message(
                "❌ No statistics found. Start using Muse to build your stats!",
                ephemeral=True
            )
            return
        
        # Get rank info
        rank_info = get_rank_from_points(stats.get('total_points', 0))
        
        # Create detailed stats embed
        embed = discord.Embed(
            title=f"📊 {interaction.user.display_name}'s Statistics",
            color=rank_info['color']
        )
        
        # User info section
        embed.add_field(
            name="👤 Profile",
            value=(
                f"**Rank:** {rank_info['name']}\n"
                f"**Points:** {stats.get('total_points', 0)}\n"
                f"**Member Since:** {stats.get('first_use_date', 'Unknown')}\n"
                f"**Premium:** {'✅ Yes' if stats.get('is_premium', False) else '❌ No'}\n"
                f"**Early User:** {'✅ Yes' if stats.get('is_early_user', False) else '❌ No'}"
            ),
            inline=True
        )
        
        # Translation stats
        embed.add_field(
            name="📝 Translation Stats",
            value=(
                f"**Total Translations:** {stats.get('total_translations', 0)}\n"
                f"**Languages Used:** {stats.get('unique_languages', 0)}\n"
                f"**Voice Sessions:** {stats.get('voice_sessions', 0)}"
            ),
            inline=True
        )
        
        # Achievement stats
        embed.add_field(
            name="🏆 Achievement Stats",
            value=(
                f"**Achievements Earned:** {len(achievements)}/{len(ACHIEVEMENTS)}\n"
                f"**Completion Rate:** {round((len(achievements) / len(ACHIEVEMENTS)) * 100, 1)}%\n"
                f"**Last Active:** {stats.get('last_active_date', 'Unknown')}"
            ),
            inline=True
        )
        
        # Show languages used if any
        languages_used = stats.get('languages_used', [])
        if languages_used:
            # Show first 10 languages with flags
            lang_display = []
            for lang_code in languages_used[:10]:
                lang_name = languages.get(lang_code, lang_code)
                flag = flag_mapping.get(lang_code, '🌐')
                lang_display.append(f"{flag} {lang_name}")
            
            lang_text = ", ".join(lang_display)
            if len(languages_used) > 10:
                lang_text += f" (+{len(languages_used) - 10} more)"
            
            embed.add_field(
                name="🌍 Languages Used",
                value=lang_text,
                inline=False
            )
        
        # Show recent achievements
        if achievements:
            recent = achievements[:3]
            recent_text = ""
            for ach in recent:
                rarity_info = RARITY_INFO.get(ach['rarity'], {})
                recent_text += f"{rarity_info.get('emoji', '⚪')} **{ach['name']}** (+{ach['points']} pts)\n"
            
            embed.add_field(
                name="🎉 Recent Achievements",
                value=recent_text,
                inline=False
            )
        
        # Add progress to next rank
        current_points = stats.get('total_points', 0)
        next_rank_points = None
        
        if current_points < 50:
            next_rank_points = 50
            next_rank = "🥉 Intermediate"
        elif current_points < 100:
            next_rank_points = 100
            next_rank = "🥈 Advanced"
        elif current_points < 250:
            next_rank_points = 250
            next_rank = "🥇 Expert"
        elif current_points < 500:
            next_rank_points = 500
            next_rank = "💎 Master"
        elif current_points < 1000:
            next_rank_points = 1000
            next_rank = "🏆 Legend"
        
        if next_rank_points:
            points_needed = next_rank_points - current_points
            embed.add_field(
                name="🎯 Next Rank",
                value=f"**{next_rank}**\n{points_needed} points needed",
                inline=True
            )
        
        # Add footer
        if interaction.guild:
            embed.set_footer(text=f"Server: {interaction.guild.name} | Use /achievements for more details")
        else:
            embed.set_footer(text="📊 Personal Statistics | Use /achievements for more details")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"My stats error: {e}")
        await interaction.response.send_message(
            "❌ An error occurred while fetching your statistics.",
            ephemeral=True
        )


# Update the Ko-fi webhook handler to work with database
@app.route('/webhook/kofi', methods=['POST'])
def handle_kofi_donation():
    try:
        data = request.json
        
        if data['type'] == 'Subscription' or (data['type'] == 'Donation' and float(data['amount']) >= 1.00):
            # Extract Discord ID from message
            message = data.get('message', '')
            
            # Try to find Discord ID in the message
            import re
            discord_id_match = re.search(r'\b(\d{17,19})\b', message)
            
            if discord_id_match:
                user_id = int(discord_id_match.group(1))
                amount = float(data['amount'])
                
                # Calculate premium duration (e.g., $1 = 30 days)
                days = int(amount * 30)
                
                # Process premium in background task (fixes asyncio.run issue)
                asyncio.create_task(process_kofi_premium(user_id, days, data))
                
                print(f"✅ Processing premium for user {user_id} - {days} days")
                return {'status': 'success', 'user_id': user_id, 'days': days}
            else:
                print(f"❌ No valid Discord ID found in message: {message}")
                return {'status': 'error', 'message': 'No Discord ID found'}
        
        return {'status': 'ignored', 'type': data.get('type')}
    except Exception as e:
        print(f"❌ Ko-fi webhook error: {e}")
        return {'status': 'error', 'message': str(e)}

# Add this new function
async def process_kofi_premium(user_id: int, days: int, kofi_data):
    """Process Ko-fi premium in background"""
    try:
        from datetime import datetime, timedelta
        expires_at = datetime.now() + timedelta(days=days)
        
        # Create user if doesn't exist
        await db.get_or_create_user(user_id, f"Ko-fi User {user_id}")
        
        # Add premium to database (use the correct method name)
        await db.update_user_premium(user_id, True, expires_at)
        
        # Add to memory for immediate effect
        tier_handler.premium_users.add(user_id)
        
        # Try to notify the user
        try:
            user = await client.fetch_user(user_id)
            embed = discord.Embed(
                title="🌟 Premium Activated via Ko-fi!",
                description=(
                    f"Thank you for your ${kofi_data['amount']} donation!\n\n"
                    f"**Premium Duration:** {days} days\n"
                    f"**Expires:** {expires_at.strftime('%B %d, %Y')}\n\n"
                    f"✨ All premium features are now active!"
                ),
                color=0x29abe0  # Ko-fi blue
            )
            await user.send(embed=embed)
            print(f"✅ Notified user {user_id} about premium activation")
        except Exception as notify_error:
            print(f"⚠️ Couldn't notify user {user_id}: {notify_error}")
            # Premium still granted, just couldn't send DM
        
        print(f"✅ Successfully granted {days} days premium to user {user_id}")
        
    except Exception as e:
        print(f"❌ Error processing Ko-fi premium for user {user_id}: {e}")
    
@tree.command(name="premium", description="Get premium access through Ko-fi")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def premium(interaction: discord.Interaction):
    user_id = interaction.user.id
    user = await db.get_or_create_user(user_id, interaction.user.display_name)
    
    if user['is_premium']:
        # User is already premium
        embed = discord.Embed(
            title="⭐ You're Already Premium!",
            description="Thank you for supporting Muse Translator!",
            color=0x2ecc71
        )
        
        embed.add_field(
            name="🎉 Your Premium Benefits",
            value=(
                "✅ Unlimited character translation\n"
                "✅ Unlimited voice translation\n"
                "✅ Full translation history\n"
                "✅ Priority support"
            ),
            inline=False
        )
        
        if user['premium_expires']:
            embed.add_field(
                name="📅 Subscription Info",
                value=f"Expires: {user['premium_expires'][:10]}",
                inline=False
            )
        
        embed.set_footer(text="Thanks for being a premium member! 💖")
        
    else:
        # User is not premium, show upgrade info
        daily_usage = await db.get_daily_usage(user_id)
        voice_minutes_used = daily_usage['voice_seconds'] // 60
        
        embed = discord.Embed(
            title="🌟 Upgrade to Premium - Just $1/month!",
            description=(
                "**Why Upgrade?**\n"
                "Remove all limits and unlock the full power of Muse Translator!"
            ),
            color=0x29abe0  # Ko-fi blue
        )
        
        embed.add_field(
            name="🆓 Free Tier (Current)",
            value=(
                "• 150 characters per translation\n"
                "• 30 minutes voice per day\n"
                "• Recent history only\n"
                f"• Today: {voice_minutes_used}/30 voice minutes used"
            ),
            inline=True
        )
        
        embed.add_field(
            name="⭐ Premium Tier ($1/month)",
            value=(
                "• **Unlimited** character translation\n"
                "• **Unlimited** voice translation\n"
                "• **Full** translation history\n"
                "• **Priority** support"
            ),
            inline=True
        )
        
        embed.add_field(
            name="💳 How to Subscribe",
            value=(
                f"1. Click the Ko-fi button below\n"
                f"2. Include your Discord ID: `{user_id}`\n"
                f"3. Set up monthly subscription ($1)\n"
                f"4. Get instant premium access!"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🔒 Secure Payment",
            value="Payments processed securely through Ko-fi",
            inline=False
        )
    
    view = discord.ui.View()
    view.add_item(discord.ui.Button(
        label="Subscribe on Ko-fi" if not user['is_premium'] else "Manage Subscription",
        url="https://ko-fi.com/muse/tiers",  # Replace with your actual Ko-fi tiers page
        style=discord.ButtonStyle.link
    ))
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

@tree.command(name="list", description="List all available languages for translation")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
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
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def invite(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Invite Muse to Your Server!",
        description="Click the link below to add me to your Discord server:",
        color=0x7289da  # Discord blue color
    )
    
    embed.add_field(
        name="🔗 Invite Link",
        value="[Click Here to Invite](https://discord.com/api/oauth2/authorize?client_id=1323041248835272724&permissions=292403422272&scope=bot+applications.commands)",
        inline=False
    )
    
    embed.add_field(
        name="✨ Features",
        value="• Real-time voice translation\n• Text translation\n• Multiple language support\n• Custom channel settings\n• Works in DMs too!",
        inline=False
    )
    
    embed.set_footer(text="Thanks for sharing Muse! 💖")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="status", description="Check your subscription status")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def check_status(interaction: discord.Interaction):
    user_id = interaction.user.id
    user = await db.get_or_create_user(user_id, interaction.user.display_name)
    daily_usage = await db.get_daily_usage(user_id)
    
    is_premium = user['is_premium']
    tier = "⭐ Premium" if is_premium else "🆓 Free"
    
    embed = discord.Embed(
        title="📊 Your Subscription Status",
        color=0x2ecc71 if is_premium else 0x3498db
    )
    
    # Account Information
    embed.add_field(
        name="👤 Account Info",
        value=(
            f"**Tier:** {tier}\n"
            f"**Member Since:** {user['created_at'][:10] if user['created_at'] else 'Today'}\n"
            f"**User ID:** {user_id}"
        ),
        inline=False
    )
    
    # Current Limits
    if is_premium:
        embed.add_field(
            name="🚀 Premium Limits",
            value=(
                "**Text Translation:** Unlimited characters per translation\n"
                "**Voice Translation:** Unlimited daily usage\n"
                "**Translation History:** Full history saved\n"
                "**Priority Support:** ✅ Enabled"
            ),
            inline=False
        )
        
        if user['premium_expires']:
            embed.add_field(
                name="📅 Subscription Details",
                value=f"**Expires:** {user['premium_expires'][:10]}",
                inline=False
            )
    else:
        embed.add_field(
            name="📋 Free Tier Limits",
            value=(
                "**Text Translation:** 150 characters per translation\n"
                "**Voice Translation:** 30 minutes per day\n"
                "**Translation History:** Recent translations only"
            ),
            inline=False
        )
    
    # Today's Usage
    voice_minutes_used = daily_usage['voice_seconds'] // 60
    voice_limit = "∞" if is_premium else "30"
    
    embed.add_field(
        name="📊 Today's Usage",
        value=(
            f"**Translations Made:** {daily_usage['translations']:,}\n"
            f"**Characters Translated:** {daily_usage['text_chars']:,}\n"
            f"**Voice Minutes Used:** {voice_minutes_used}/{voice_limit} minutes"
        ),
        inline=False
    )
    
    # Usage warnings for free users
    if not is_premium:
        warnings = []
        
        # Check if approaching voice limit
        if voice_minutes_used >= 25:  # 25+ minutes used
            warnings.append("⚠️ Voice limit almost reached!")
        
        if warnings:
            embed.add_field(
                name="⚠️ Usage Warnings",
                value="\n".join(warnings),
                inline=False
            )
        
        embed.add_field(
            name="💡 Upgrade Benefits",
            value=(
                "Upgrade to Premium for just $1/month:\n"
                "• Remove all character limits\n"
                "• Unlimited voice translation\n"
                "• Full translation history\n"
                "• Priority support\n\n"
                "Use `/premium` to upgrade now!"
            ),
            inline=False
        )
    
    # Add footer with context info
    if interaction.guild:
        embed.set_footer(text=f"Server: {interaction.guild.name}")
    else:
        embed.set_footer(text="📱 User Mode Status")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Add new command for translation history
@tree.command(name="history", description="View your recent translation history")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(limit="Number of translations to show (max 20)")
async def translation_history(interaction: discord.Interaction, limit: int = 10):
    user_id = interaction.user.id
    
    # Get user to check premium status
    user = await db.get_or_create_user(user_id, interaction.user.display_name)
    
    # Limit based on tier
    if not user['is_premium']:
        limit = min(limit, 10)  # Free users get max 10
    else:
        limit = min(limit, 20)  # Premium users get max 20
    
    # Get translation history using your database method
    history = await db.get_translation_history(user_id, limit)
    
    if not history:
        embed = discord.Embed(
            title="📚 Translation History",
            description="No translations found. Start translating to build your history!",
            color=0x95a5a6
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    embed = discord.Embed(
        title="📚 Your Translation History",
        description=f"Showing your {len(history)} most recent translations",
        color=0x2ecc71 if user['is_premium'] else 0x3498db
    )
    
    for i, translation in enumerate(history, 1):
        # Get language names and flags
        source_name = languages.get(translation['source_lang'], translation['source_lang'])
        target_name = languages.get(translation['target_lang'], translation['target_lang'])
        source_flag = flag_mapping.get(translation['source_lang'], '🌐')
        target_flag = flag_mapping.get(translation['target_lang'], '🌐')
        
        # Format the translation entry - USE CORRECT FIELD NAMES
        original_text = translation['original'][:100] + "..." if len(translation['original']) > 100 else translation['original']
        translated_text = translation['translated'][:100] + "..." if len(translation['translated']) > 100 else translation['translated']
        
        embed.add_field(
            name=f"{i}. {source_flag} {source_name} → {target_flag} {target_name} ({translation['type']})",
            value=f"**Original:** {original_text}\n**Translation:** {translated_text}",
            inline=False
        )
    
    # Add tier info
    if user['is_premium']:
        embed.set_footer(text="⭐ Premium: Full history access")
    else:
        embed.set_footer(text="🆓 Free: Recent history only • /premium for full access")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)


# Add new command for setting user preferences
@tree.command(name="preferences", description="Set your default translation languages")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(
    default_source="Your default source language (or 'auto' for detection)",
    default_target="Your default target language"
)
async def set_preferences(
    interaction: discord.Interaction,
    default_source: str,
    default_target: str
):
    user_id = interaction.user.id
    
    # Convert language inputs to codes
    source_code = "auto" if default_source.lower() == "auto" else get_language_code(default_source)
    target_code = get_language_code(default_target)
    
    # Validate language codes
    if default_source.lower() != "auto" and not source_code:
        await interaction.response.send_message(
            f"❌ Invalid source language: '{default_source}'\nUse /list to see available languages or use 'auto' for automatic detection.",
            ephemeral=True
        )
        return
        
    if not target_code:
        await interaction.response.send_message(
            f"❌ Invalid target language: '{default_target}'\nUse /list to see available languages.",
            ephemeral=True
        )
        return
    
    # Save preferences to database
    await db.update_user_preferences(user_id, source_code, target_code)
    
    # Get display names
    source_display = "Auto-detect" if source_code == "auto" else languages.get(source_code, source_code)
    target_display = languages.get(target_code, target_code)
    source_flag = '🔍' if source_code == "auto" else flag_mapping.get(source_code, '🌐')
    target_flag = flag_mapping.get(target_code, '🌐')
    
    embed = discord.Embed(
        title="✅ Preferences Updated!",
        description=(
            f"Your default languages have been set:\n\n"
            f"**Default Source:** {source_flag} {source_display}\n"
            f"**Default Target:** {target_flag} {target_display}\n\n"
            f"These will be suggested in future commands with autocomplete."
        ),
        color=0x2ecc71
    )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Add autocomplete to preferences command
set_preferences.autocomplete('default_source')(source_language_autocomplete)
set_preferences.autocomplete('default_target')(language_autocomplete)

@tree.command(name="help", description="Show all available commands")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="🤖 Muse Translator - Command List",
        description="Here are all available commands:",
        color=0x3498db
    )
    
    # Check if we're in server or user context
    is_server = interaction.guild is not None
    
    # Check if user is premium for personalized help
    user_id = interaction.user.id
    user = await db.get_or_create_user(user_id, interaction.user.display_name)
    is_premium = user['is_premium']
    
    # Text Translation Commands
    embed.add_field(
        name="📝 Text Translation",
        value=(
            "`/texttr [text] [source_lang] [target_lang]` - Translate text\n"
            "`/read [target_lang] [message_id]` - Translate message by ID\n"
            "`/dmtr [user] [text] [source_lang] [target_lang]` - Send translated DM" + 
            (" (server only)" if not is_server else "")
        ),
        inline=False
    )
    
    # Voice Commands
    voice_commands = (
        "`/voice [text] [source_lang] [target_lang]` - Text to speech\n"
        "`/speak [text] [source_lang] [target_lang]` - Play speech in voice channel" +
        (" (server only)" if not is_server else "") + "\n"
        "`/voicechat [source_lang] [target_lang]` - Real-time voice translation" +
        (" (server only)" if not is_server else "") + "\n"
        "`/voicechat2 [lang1] [lang2]` - Enhanced bidirectional voice translation" +
        (" (server only)" if not is_server else "")
    )
    
    embed.add_field(
        name="🎤 Voice Commands",
        value=voice_commands,
        inline=False
    )
    
    # Auto Translation (server only)
    if is_server:
        embed.add_field(
            name="🔄 Auto Translation (Server Only)",
            value="`/autotranslate [source_lang] [target_lang]` - Auto-translate your messages",
            inline=False
        )
    
    # Setup & Control Commands
    setup_commands = "`/start` - Initialize translator\n"
    if is_server:
        setup_commands += "`/setchannel [channel_id]` - Set translation channel\n"
    setup_commands += "`/stop` - Stop active translation sessions"
    
    embed.add_field(
        name="⚙️ Setup & Control",
        value=setup_commands,
        inline=False
    )
    
    # Settings Commands
    embed.add_field(
        name="🎛️ Settings",
        value=(
            "`/hide` - Hide original text in translations\n"
            "`/show` - Show original text in translations\n"
            "`/preferences [source] [target]` - Set default languages"
        ),
        inline=False
    )
    
    # Information Commands
    embed.add_field(
        name="ℹ️ Information",
        value=(
            "`/list` - Show all supported languages\n"
            "`/stats` - View your translation statistics\n"
            "`/history [limit]` - View recent translation history\n"
            "`/status` - Check your subscription status\n"
            "`/premium` - Get premium access info\n"
            "`/invite` - Get bot invite links\n"
            "`/help` - Show this command list"
        ),
        inline=False
    )
    
    # Context Menu Commands
    embed.add_field(
        name="📱 Context Menu",
        value="`Right-click message` → `Apps` → `Read Message` - Translate any message",
        inline=False
    )
    
    # Add usage limits info
    if is_premium:
        embed.add_field(
            name="⭐ Your Premium Limits",
            value=(
                "• **Text:** Unlimited characters per translation\n"
                "• **Voice:** Unlimited daily usage\n"
                "• **History:** Full translation history saved"
            ),
            inline=False
        )
    else:
        embed.add_field(
            name="🆓 Your Free Limits",
            value=(
                "• **Text:** 150 characters per translation\n"
                "• **Voice:** 30 minutes per day\n"
                "• **History:** Recent translations only\n"
                "• Use `/premium` to upgrade for unlimited access!"
            ),
            inline=False
        )
    
    # Add usage tips
    embed.add_field(
        name="💡 Usage Tips",
        value=(
            "• Use `auto` as source language for automatic detection\n"
            "• Language codes: `en`, `es`, `fr` or names: `English`, `Spanish`, `French`\n"
            "• Example: `/texttr text:'Hello' source_lang:en target_lang:es`"
        ),
        inline=False
    )
    
    # Add context-specific footer
    if is_server:
        embed.set_footer(text=f"Server Mode: {interaction.guild.name} | All features available")
    else:
        embed.set_footer(text="User Mode: Perfect for DMs | Some features are server-only")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)
@tree.command(name="feedback", description="Leave feedback for the bot (1-5 stars)")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(
    rating="Rate the bot from 1-5 stars",
    message="Optional feedback message"
)
async def submit_feedback(
    interaction: discord.Interaction,
    rating: int,
    message: str = None
):
    # Validate rating
    if rating < 1 or rating > 5:
        await interaction.response.send_message(
            "❌ Rating must be between 1 and 5 stars!",
            ephemeral=True
        )
        return
    
    try:
        # Add feedback to database
        await feedback_db.add_feedback(
            user_id=interaction.user.id,
            username=interaction.user.display_name,
            rating=rating,
            message=message
        )
        
        # Create response
        stars = "⭐" * rating
        response = f"✅ Thank you for your feedback!\n{stars} **{rating}/5 stars**"
        
        if message:
            response += f"\n💬 Message: \"{message}\""
        
        await interaction.response.send_message(response, ephemeral=True)
        
        # Send notification to a specific channel (optional)
        # Replace FEEDBACK_CHANNEL_ID with your channel ID
        FEEDBACK_CHANNEL_ID = 1234567890123456789  # Replace with your channel ID
        feedback_channel = client.get_channel(FEEDBACK_CHANNEL_ID)
        
        if feedback_channel:
            embed = discord.Embed(
                title="📝 New Feedback Received!",
                color=0x00ff00 if rating >= 4 else 0xff9900 if rating == 3 else 0xff0000
            )
            embed.add_field(name="User", value=interaction.user.display_name, inline=True)
            embed.add_field(name="Rating", value=f"{stars} {rating}/5", inline=True)
            embed.add_field(name="Server", value=interaction.guild.name if interaction.guild else "DM", inline=True)
            
            if message:
                embed.add_field(name="Message", value=message, inline=False)
            
            await feedback_channel.send(embed=embed)
        
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Error saving feedback: {str(e)}",
            ephemeral=True
        )

@tree.command(name="reviews", description="View recent feedback and ratings")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def view_reviews(interaction: discord.Interaction):
    try:
        # Get statistics
        stats = await feedback_db.get_stats()
        
        # Get recent feedback
        recent_feedback = await feedback_db.get_all_feedback(limit=10)
        
        # Create embed
        embed = discord.Embed(
            title="📊 Bot Reviews & Feedback",
            color=0x3498db
        )
        
        # Add statistics
        if stats["total"] > 0:
            embed.add_field(
                name="⭐ Overall Rating",
                value=f"**{stats['avg_rating']}/5.0** stars\nFrom {stats['total']} reviews",
                inline=True
            )
            
            # Rating breakdown
            rating_breakdown = (
                f"5⭐: {stats['five_star']}\n"
                f"4⭐: {stats['four_star']}\n"
                f"3⭐: {stats['three_star']}\n"
                f"2⭐: {stats['two_star']}\n"
                f"1⭐: {stats['one_star']}"
            )
            
            embed.add_field(
                name="📈 Rating Breakdown",
                value=rating_breakdown,
                inline=True
            )
        else:
            embed.add_field(
                name="📝 No Reviews Yet",
                value="Be the first to leave feedback with `/feedback`!",
                inline=False
            )
        
        # Add recent reviews
        if recent_feedback:
            recent_text = ""
            for feedback in recent_feedback[:5]:  # Show top 5
                stars = "⭐" * feedback["rating"]
                date = feedback["created_at"][:10]  # Just the date
                
                if feedback["message"]:
                    message_preview = feedback["message"][:50] + "..." if len(feedback["message"]) > 50 else feedback["message"]
                    recent_text += f"{stars} **{feedback['username']}** ({date})\n*\"{message_preview}\"*\n\n"
                else:
                    recent_text += f"{stars} **{feedback['username']}** ({date})\n\n"
            
            embed.add_field(
                name="💬 Recent Reviews",
                value=recent_text[:1024],  # Discord field limit
                inline=False
            )
        
        embed.set_footer(text="Leave your own review with /feedback [rating] [message]")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(
            f"❌ Error loading reviews: {str(e)}",
            ephemeral=True
        )

@tree.command(name="addpremium", description="[ADMIN] Grant premium access to any Discord user", guild=discord.Object(id=YOUR_SERVER_ID))
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    user="Any Discord user to grant premium to",
    days="Number of days of premium (default: 30)"
)
async def add_premium(interaction: discord.Interaction, user: discord.User, days: int = 30):
    # Double security: Must be admin in YOUR server AND be you
    if interaction.user.id != YOUR_ADMIN_ID:
        await interaction.response.send_message("❌ Bot owner only!", ephemeral=True)
        return
    
    try:
        from datetime import datetime, timedelta
        expires_at = datetime.now() + timedelta(days=days)
        
        # Add to database (you'll need to implement this)
        # await db.get_or_create_user(user.id, user.display_name)
        # await db.update_user_premium(user.id, True, expires_at)
        
        # Add to memory
        tier_handler.premium_users.add(user.id)
        
        # Success message
        embed = discord.Embed(
            title="✅ Premium Granted Successfully",
            description=(
                f"**User:** {user.display_name} (`{user.id}`)\n"
                f"**Duration:** {days} days\n"
                f"**Expires:** {expires_at.strftime('%Y-%m-%d %H:%M UTC')}\n\n"
                f"✨ *Global premium access activated*"
            ),
            color=0x00ff00
        )
        
        if user.avatar:
            embed.set_thumbnail(url=user.avatar.url)
            
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Try to notify the user
        try:
            user_embed = discord.Embed(
                title="🌟 Premium Access Granted!",
                description=(
                    f"You've been granted **{days} days** of premium access for Muse Translator!\n\n"
                    f"**Expires:** {expires_at.strftime('%B %d, %Y at %H:%M UTC')}\n\n"
                    f"**Premium Features Unlocked:**\n"
                    f"• ♾️ Unlimited text translation\n"
                    f"• 🎤 Extended voice translation\n"
                    f"• ⚡ Priority support"
                ),
                color=0xffd700
            )
            await user.send(embed=user_embed)
            
            await interaction.followup.send("✅ User has been notified via DM", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("⚠️ Couldn't notify user (DMs disabled)", ephemeral=True)
        except Exception as dm_error:
            await interaction.followup.send(f"⚠️ Couldn't notify user: {dm_error}", ephemeral=True)
            
    except Exception as e:
        await interaction.response.send_message(f"❌ Error granting premium: {str(e)}", ephemeral=True)

@tree.command(name="removepremium", description="[ADMIN] Remove premium access from any Discord user", guild=discord.Object(id=YOUR_SERVER_ID))
@app_commands.default_permissions(administrator=True)
@app_commands.describe(user="Any Discord user to remove premium from")
async def remove_premium(interaction: discord.Interaction, user: discord.User):
    if interaction.user.id != YOUR_ADMIN_ID:
        await interaction.response.send_message("❌ Bot owner only!", ephemeral=True)
        return
    
    try:
        # Remove from memory
        tier_handler.premium_users.discard(user.id)
        
        # Success message
        embed = discord.Embed(
            title="✅ Premium Removed Successfully",
            description=(
                f"**User:** {user.display_name} (`{user.id}`)\n"
                f"Premium access has been revoked."
            ),
            color=0xff9900
        )
        
        if user.avatar:
            embed.set_thumbnail(url=user.avatar.url)
            
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Try to notify the user
        try:
            user_embed = discord.Embed(
                title="⏰ Premium Access Ended",
                description=(
                    "Your premium access for Muse Translator has been removed.\n\n"
                    "**What this means:**\n"
                    "• Text translations limited to 100 characters\n"
                    "• Voice translations limited to 30 minutes daily\n\n"
                    "Use `/premium` to subscribe again if you'd like premium features."
                ),
                color=0xff9900
            )
            await user.send(embed=user_embed)
            
            await interaction.followup.send("✅ User has been notified via DM", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("⚠️ Couldn't notify user (DMs disabled)", ephemeral=True)
        except Exception as dm_error:
            await interaction.followup.send(f"⚠️ Couldn't notify user: {dm_error}", ephemeral=True)
            
    except Exception as e:
        await interaction.response.send_message(f"❌ Error removing premium: {str(e)}", ephemeral=True)

@tree.command(name="listpremium", description="[ADMIN] List all premium users", guild=discord.Object(id=YOUR_SERVER_ID))
@app_commands.default_permissions(administrator=True)
async def list_premium(interaction: discord.Interaction):
    if interaction.user.id != YOUR_ADMIN_ID:
        await interaction.response.send_message("❌ Bot owner only!", ephemeral=True)
        return
    
    try:
        premium_list = list(tier_handler.premium_users)
        
        if not premium_list:
            embed = discord.Embed(
                title="📋 Premium Users List",
                description="No premium users found.",
                color=0x95a5a6
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Create embed with premium users
        embed = discord.Embed(
            title="👑 Premium Users List",
            description=f"**Total Premium Users:** {len(premium_list)}",
            color=0xffd700
        )
        
        # Show first 10 users
        user_list = []
        for i, user_id in enumerate(premium_list[:10]):
            try:
                user = await client.fetch_user(user_id)
                user_list.append(f"{i+1}. **{user.display_name}** (`{user_id}`)")
            except:
                user_list.append(f"{i+1}. **Unknown User** (`{user_id}`)")
        
        embed.add_field(
            name="Premium Users",
            value="\n".join(user_list) if user_list else "None",
            inline=False
        )
        
        if len(premium_list) > 10:
            embed.add_field(
                name="Note",
                value=f"Showing first 10 of {len(premium_list)} users",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Error listing premium users: {str(e)}", ephemeral=True)

@tree.command(name="checkuser", description="[ADMIN] Check any Discord user's premium status", guild=discord.Object(id=YOUR_SERVER_ID))
@app_commands.default_permissions(administrator=True)
@app_commands.describe(user="Any Discord user to check")
async def check_user(interaction: discord.Interaction, user: discord.User):
    if interaction.user.id != YOUR_ADMIN_ID:
        await interaction.response.send_message("❌ Bot owner only!", ephemeral=True)
        return
    
    try:
        embed = discord.Embed(
            title=f"👤 User Profile: {user.display_name}",
            color=0x3498db
        )
        
        # Add user avatar
        if user.avatar:
            embed.set_thumbnail(url=user.avatar.url)
        
        # Basic user info
        embed.add_field(name="Discord Username", value=user.display_name, inline=True)
        embed.add_field(name="User ID", value=f"`{user.id}`", inline=True)
        embed.add_field(name="Account Created", value=user.created_at.strftime('%Y-%m-%d'), inline=True)
        
        # Premium status
        is_premium = user.id in tier_handler.premium_users
        limits = tier_handler.get_limits(user.id)
        
        if is_premium:
            embed.add_field(name="Premium Status", value="✅ ACTIVE", inline=True)
            embed.add_field(name="Text Limit", value="♾️ Unlimited", inline=True)
            embed.add_field(name="Voice Limit", value="♾️ Unlimited", inline=True)
            embed.color = 0x00ff00
        else:
            embed.add_field(name="Premium Status", value="❌ NOT PREMIUM", inline=True)
            embed.add_field(name="Text Limit", value=f"{limits['text_limit']} characters", inline=True)
            embed.add_field(name="Voice Limit", value=f"{limits['voice_limit']} seconds daily", inline=True)
            embed.color = 0x95a5a6
        
        embed.set_footer(text=f"Admin Panel • Server: {interaction.guild.name}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Error checking user: {str(e)}", ephemeral=True)

# Separate sync command for guild commands
@tree.command(name="syncguild", description="[ADMIN] Sync guild commands", guild=discord.Object(id=YOUR_SERVER_ID))
@app_commands.default_permissions(administrator=True)
async def sync_guild(interaction: discord.Interaction):
    if interaction.user.id != YOUR_ADMIN_ID:
        await interaction.response.send_message("❌ Bot owner only!", ephemeral=True)
        return
    
    try:
        guild = discord.Object(id=YOUR_SERVER_ID)
        synced = await tree.sync(guild=guild)
        
        embed = discord.Embed(
            title="🔄 Guild Commands Synced",
            description=(
                f"**Commands Synced:** {len(synced)}\n"
                f"**Server:** {interaction.guild.name}\n"
                f"**Server ID:** `{YOUR_SERVER_ID}`"
            ),
            color=0x00ff00
        )
        
        # List synced commands
        if synced:
            command_list = [f"• `/{cmd.name}` - {cmd.description}" for cmd in synced]
            embed.add_field(
                name="Synced Commands",
                value="\n".join(command_list[:10]),  # Show first 10
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        await interaction.response.send_message(f"❌ Sync failed: {str(e)}", ephemeral=True)
# Add global error handler for better error management
@tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.TransformerError):
        # Handle member conversion errors
        if "Member" in str(error):
            await interaction.response.send_message(
                "❌ Invalid user! Please mention a valid server member.",
                ephemeral=True
            )
            return
    elif isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message(
            "❌ You don't have permission to use this command.",
            ephemeral=True
        )
        return
    
    # Log other errors
    print(f"App command error: {error}")
    if not interaction.response.is_done():
        await interaction.response.send_message(
            "❌ An unexpected error occurred while processing the command.",
            ephemeral=True
        )

@client.event
async def on_ready():
    print("🚀 Bot is starting up...")
    
    # Initialize feedback database
    try:
        await feedback_db.initialize()
        print("✅ Feedback database initialized!")
    except Exception as e:
        print(f"❌ Feedback database error: {e}")
    
    # Initialize main database - use the correct method name
    try:
        await db.init_db()  # Changed from db.initialize() to db.init_db()
        print("✅ Main database initialized!")
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")

    # Initialize achievement system
    try:
        achievement_db.init_database()
        print("✅ Achievement system initialized")
    except Exception as e:
        print(f"⚠️ Achievement system error: {e}")
    
    # Load premium users - we'll create this method
    try:
        premium_users = await db.get_premium_users()
        tier_handler.premium_users.update(premium_users)
        print(f"✅ Loaded {len(premium_users)} premium users")
    except Exception as e:
        print(f"❌ Error loading premium users: {e}")
        # Fallback to hardcoded premium user
        tier_handler.premium_users.add(1192196672437096520)
        print("✅ Loaded hardcoded premium users")
    
    # Sync commands
    try:
        # Sync global commands (regular bot commands)
        synced_global = await tree.sync()
        print(f"✅ Global commands synced: {len(synced_global)}")
        
        # Sync guild commands (admin commands) to your server
        guild = discord.Object(id=YOUR_SERVER_ID)
        synced_guild = await tree.sync(guild=guild)
        print(f"✅ Guild commands synced: {len(synced_guild)} to server {guild.id}")
        
    except Exception as e:
        print(f"🔄 Sync status: {e}")
    
    print(f"✨ Bot is ready! Logged in as {client.user}")
    print(f"📊 Connected to {len(client.guilds)} servers")

# Helper function to get premium users using your database structure
async def get_premium_users_from_db():
    """Get all premium user IDs using your existing database structure"""
    import aiosqlite
    premium_users = set()
    
    async with aiosqlite.connect(db.db_path) as conn:
        async with conn.execute("SELECT user_id FROM users WHERE is_premium = TRUE") as cursor:
            users = await cursor.fetchall()
            premium_users = {user[0] for user in users}
    
    return premium_users


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
