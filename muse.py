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
import asyncio
import atexit
from typing import Dict, Any, Optional
from dotenv import load_dotenv
import json
import os
from os import system
import paypalrestsdk 
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
from achievement_system import achievement_db, get_rank_from_points, send_achievement_notification, ACHIEVEMENTS, RARITY_INFO, RANK_BADGES
from reward_system import (
    RewardDatabase, 
    REWARDS, 
    AUTO_BADGES, 
    RANK_BADGES,
    get_enhanced_user_limits,
    has_priority_processing,
    has_enhanced_voice_access,
    reward_db  
)
from discord.ui import View, Button
from add_streak_column import add_streak_column, check_column_exists
from i18n.translate import t
import pytesseract
from PIL import Image


pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
ffmpeg_path = r"C:\Users\shoub\Downloads\ffmpeg\ffmpeg-master-latest-win64-gpl-shared\bin\ffmpeg.exe"

new_achievements = []
YOUR_ADMIN_ID = 1192196672437096520
YOUR_SERVER_ID = 1332522833326375022
# Tier colors for embeds
TIER_COLORS = {
    'free': 0x95a5a6,      # Gray
    'basic': 0x3498db,     # Blue  
    'premium': 0xf39c12,   # Orange
    'pro': 0x9b59b6        # Purple
}
# Global translation cache
translations_cache: Dict[str, Dict[str, Any]] = {}

# Supported UI languages (add more as you create JSON files)
SUPPORTED_UI_LANGUAGES = {
    file.replace(".json", "")
    for file in os.listdir("i18n")
    if file.endswith(".json")
} # Start with these two
TIER_EMOJIS = {
    'free': '🆓',
    'basic': '🥉',
    'premium': '🥈',
    'pro': '🥇'
}
# Somewhere global
MEDIA_LIMITS_MB = {
    "free": 4,      # below 8MB Discord limit
    "basic": 8,
    "premium": 20,
    "pro": 50       # Nitro user cap
}

# Add this after your imports and before your classes
RANK_BADGES = {
    0: {'name': 'Newcomer', 'emoji': '🆕', 'color': 0x95a5a6},
    50: {'name': 'Beginner', 'emoji': '🌱', 'color': 0x2ecc71},
    150: {'name': 'Learner', 'emoji': '📈', 'color': 0x3498db},
    300: {'name': 'Dedicated', 'emoji': '🎯', 'color': 0x9b59b6},
    500: {'name': 'Expert', 'emoji': '⭐', 'color': 0xf1c40f},
    1000: {'name': 'Master', 'emoji': '👑', 'color': 0xe67e22},
    2000: {'name': 'Legend', 'emoji': '🏆', 'color': 0xe74c3c},
    5000: {'name': 'Grandmaster', 'emoji': '💎', 'color': 0x1abc9c}
}
print("🔧 Setting up database schema...")
# Wait for database to be initialized first, then add column
async def setup_streak_column():
    """Add streak column after database is initialized"""
    try:
        # Wait a moment for database to be ready
        import asyncio
        await asyncio.sleep(1)
        
        # Now add the column
        column_added = add_streak_column()
        global HAS_STREAK_COLUMN
        HAS_STREAK_COLUMN = column_added or check_column_exists()
        
        if HAS_STREAK_COLUMN:
            print("✅ Streak system ready!")
        else:
            print("⚠️ Running without streak system")
            
    except Exception as e:
        print(f"Error setting up streak column: {e}")
        HAS_STREAK_COLUMN = False

# Initialize as False
HAS_STREAK_COLUMN = False
# Pro Tier Processing Function
def format_seconds(seconds: int) -> str:
    """Format seconds as 'X min Y sec' or 'Y sec'."""
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    if minutes > 0:
        return f"{minutes} min {secs} sec"
    else:
        return f"{secs} sec"
async def process_kofi_pro_tier(user_id: int, days: int, kofi_data, tier_name: str):
    """Process Ko-fi pro tier subscription with achievement tracking"""
    try:
        from datetime import datetime, timedelta
        expires_at = datetime.now() + timedelta(days=days)
        
        # Create user if doesn't exist
        await db.get_or_create_user(user_id, f"Ko-fi User {user_id}")
        
        # Add to pro tier (highest tier)
        tier_handler.pro_users.add(user_id)
        
        # Update database
        await db.update_user_premium(user_id, True, expires_at)
        
        # 🏆 TRACK PRO TIER ACHIEVEMENT
        try:
            achievement_db.track_premium_purchase(user_id)
            
            # Check for new achievements
            new_achievements = achievement_db.check_achievements(user_id)
            if new_achievements:
                await send_achievement_notification(client, user_id, new_achievements)
        except Exception as e:
            logger.error(f"Error tracking pro achievements: {e}")
        
        # Notify user
        await send_tier_notification(user_id, "Pro", tier_name, kofi_data, expires_at, days, "🚀")
        logger.info(f"✅ Successfully granted {days} days pro tier to user {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Error processing Ko-fi pro tier for user {user_id}: {e}")
# File-based storage functions
INVITE_DATA_FILE = "invite_data.json"
def load_translations():
    """Load all translation files into memory"""
    global translations_cache
    
    for lang_code in SUPPORTED_UI_LANGUAGES:
        try:
            with open(f'i18n/{lang_code}.json', 'r', encoding='utf-8') as f:
                translations_cache[lang_code] = json.load(f)
        except FileNotFoundError:
            print(f"Warning: Translation file i18n/{lang_code}.json not found")
        except json.JSONDecodeError as e:
            print(f"Error loading translation file {lang_code}.json: {e}")

def get_translation(lang_code: str, key: str, **kwargs) -> str:
    """
    Get translated text for a given language and key
    
    Args:
        lang_code: Language code (e.g., 'en', 'es')
        key: Translation key (e.g., 'PREF_UPDATED' or 'ERROR_INVALID_SOURCE')
        **kwargs: Format parameters for the translation string
    
    Returns:
        Translated and formatted string
    """
    # Fallback to English if language not supported
    if lang_code not in SUPPORTED_UI_LANGUAGES:
        lang_code = 'en'
    
    # Get translation from cache
    lang_translations = translations_cache.get(lang_code, translations_cache.get('en', {}))
    
    # Handle nested keys (e.g., 'TRANSLATION.title')
    keys = key.split('.')
    translation = lang_translations
    
    for k in keys:
        if isinstance(translation, dict) and k in translation:
            translation = translation[k]
        else:
            # Fallback to English if key not found
            english_translation = translations_cache.get('en', {})
            for ek in keys:
                if isinstance(english_translation, dict) and ek in english_translation:
                    english_translation = english_translation[ek]
                else:
                    return f"[Missing: {key}]"  # Last resort
            translation = english_translation
            break
    
    # Format the translation if it's a string
    if isinstance(translation, str) and kwargs:
        try:
            return translation.format(**kwargs)
        except KeyError as e:
            print(f"Missing format parameter {e} for key {key}")
            return translation
    
    return translation if isinstance(translation, str) else f"[Invalid: {key}]"

async def get_user_ui_language(user_id: int) -> str:
    """Get user's UI language preference"""
    # Use your existing database function
    ui_lang = await db.get_user_ui_language(user_id)
    return ui_lang if ui_lang in SUPPORTED_UI_LANGUAGES else 'en'

# Load translations when the bot starts
load_translations()

def load_invite_data():
    """Load invite data from JSON file"""
    try:
        if os.path.exists(INVITE_DATA_FILE):
            with open(INVITE_DATA_FILE, 'r') as f:
                return json.load(f)
        return {"invite_requests": [], "successful_invites": []}
    except Exception as e:
        logger.error(f"Error loading invite data: {e}")
        return {"invite_requests": [], "successful_invites": []}

def save_invite_data(data):
    """Save invite data to JSON file"""
    try:
        with open(INVITE_DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        logger.error(f"Error saving invite data: {e}")

def store_invite_request(user_id: int):
    """Store that a user requested an invite link"""
    try:
        data = load_invite_data()
        
        data["invite_requests"].append({
            "user_id": user_id,
            "requested_at": datetime.now().isoformat()
        })
        
        # Keep only last 1000 requests to prevent file from getting too large
        if len(data["invite_requests"]) > 1000:
            data["invite_requests"] = data["invite_requests"][-1000:]
        
        save_invite_data(data)
        
    except Exception as e:
        logger.error(f"Error storing invite request: {e}")

def get_recent_invite_requester(guild):
    """Check if any user recently requested an invite and is in this guild"""
    try:
        data = load_invite_data()
        
        # Get users who requested invites in the last 24 hours
        cutoff_time = datetime.now() - timedelta(hours=24)
        
        recent_requesters = []
        for request in data["invite_requests"]:
            request_time = datetime.fromisoformat(request["requested_at"])
            if request_time > cutoff_time:
                recent_requesters.append(request["user_id"])
        
        # Check if any of these users are in the new guild
        for user_id in recent_requesters:
            member = guild.get_member(user_id)
            if member:
                logger.info(f"Found recent invite requester in guild: {user_id}")
                return user_id
        
        return None
        
    except Exception as e:
        logger.error(f"Error getting recent invite requester: {e}")
        return None

async def process_successful_invite(inviter_id: int, guild):
    """Process a successful server invitation - LINKED TO ACHIEVEMENT SYSTEM"""
    try:
        data = load_invite_data()
        
        # Record the successful invitation
        data["successful_invites"].append({
            "inviter_id": inviter_id,
            "guild_id": guild.id,
            "guild_name": guild.name,
            "member_count": guild.member_count,
            "invited_at": datetime.now().isoformat()
        })
        
        save_invite_data(data)
        
        # 🎯 LINK TO REWARD SYSTEM - Award points
        reward_db.add_points(inviter_id, 25, f"Successfully invited Muse to {guild.name}")
        
        # 🎯 LINK TO ACHIEVEMENT SYSTEM - Update stats
        achievement_db.track_stat(inviter_id, 'servers_invited', 1)
        
        logger.info(f"✅ Processed successful invite for user {inviter_id}")
        
    except Exception as e:
        logger.error(f"Error processing successful invite: {e}")

async def check_server_inviter_achievement(inviter_id: int):
    """Check and award the server inviter achievement - LINKED TO ACHIEVEMENT SYSTEM"""
    try:
        data = load_invite_data()
        
        # Count successful invites for this user
        total_invites = sum(1 for invite in data["successful_invites"] 
                          if invite["inviter_id"] == inviter_id)
        
        # Check if they should get the achievement
        if total_invites >= 1:
            # 🎯 LINK TO ACHIEVEMENT SYSTEM - Check existing achievements
            user_achievements = achievement_db.get_user_achievements(inviter_id)
            achievement_ids = [ach['id'] for ach in user_achievements]
            
            if 'server_inviter' not in achievement_ids:
                # 🎯 LINK TO ACHIEVEMENT SYSTEM - Award the achievement
                achievement_db.award_achievement(inviter_id, 'server_inviter', 120)
                
                # 🎯 LINK TO ACHIEVEMENT SYSTEM - Send notification
                await send_achievement_notification(client, inviter_id, ['server_inviter'])
                
                logger.info(f"🏆 Awarded Muse Ambassador achievement to user {inviter_id}")
        
    except Exception as e:
        logger.error(f"Error checking server inviter achievement: {e}")

# Premium Tier Processing Function
async def process_kofi_premium_tier(user_id: int, days: int, kofi_data, tier_name: str):
    """Process Ko-fi premium tier subscription with achievement tracking"""
    try:
        from datetime import datetime, timedelta
        expires_at = datetime.now() + timedelta(days=days)
        
        # Create user if doesn't exist
        await db.get_or_create_user(user_id, f"Ko-fi User {user_id}")
        
        # Add to premium tier
        tier_handler.premium_users.add(user_id)
        
        # Update database
        await db.update_user_premium(user_id, True, expires_at)
        
        # 🏆 TRACK PREMIUM ACHIEVEMENT
        try:
            achievement_db.track_premium_purchase(user_id)
            
            # Check for new achievements
            new_achievements = achievement_db.check_achievements(user_id)
            if new_achievements:
                await send_achievement_notification(client, user_id, new_achievements)
        except Exception as e:
            logger.error(f"Error tracking premium achievements: {e}")
        
        # Notify user
        await send_tier_notification(user_id, "Premium", tier_name, kofi_data, expires_at, days, "⭐")
        logger.info(f"✅ Successfully granted {days} days premium tier to user {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Error processing Ko-fi premium tier for user {user_id}: {e}")

# Basic Tier Processing Function
async def process_kofi_basic_tier(user_id: int, days: int, kofi_data, tier_name: str):
    """Process Ko-fi basic tier subscription with achievement tracking"""
    try:
        from datetime import datetime, timedelta
        expires_at = datetime.now() + timedelta(days=days)
        
        # Create user if doesn't exist
        await db.get_or_create_user(user_id, f"Ko-fi User {user_id}")
        
        # Add to basic tier
        tier_handler.basic_users.add(user_id)
        
        # Update database
        await db.update_user_premium(user_id, True, expires_at)
        
        # 🏆 TRACK BASIC TIER ACHIEVEMENT
        try:
            achievement_db.track_premium_purchase(user_id)
            
            # Check for new achievements
            new_achievements = achievement_db.check_achievements(user_id)
            if new_achievements:
                await send_achievement_notification(client, user_id, new_achievements)
        except Exception as e:
            logger.error(f"Error tracking basic achievements: {e}")
        
        # Notify user
        await send_tier_notification(user_id, "Basic", tier_name, kofi_data, expires_at, days, "💎")
        logger.info(f"✅ Successfully granted {days} days basic tier to user {user_id}")
        
    except Exception as e:
        logger.error(f"❌ Error processing Ko-fi basic tier for user {user_id}: {e}")

# Unified tier notification function
async def send_tier_notification(user_id: int, tier: str, tier_name: str, kofi_data, expires_at, days: int, emoji: str):
    """Send notification to user about their new tier subscription"""
    try:
        user = await client.fetch_user(user_id)
        
        # Tier-specific colors
        colors = {
            "Pro": 0x9b59b6,      # Purple for Pro ($5/month)
            "Premium": 0xf39c12,  # Orange for Premium ($3/month)  
            "Basic": 0x3498db     # Blue for Basic ($1/month)
        }
        
        embed = discord.Embed(
            title=f"{emoji} {tier} Subscription Activated!",
            description=(
                f"Thank you for your **{tier_name}** subscription!\n\n"
                f"**Amount:** ${kofi_data['amount']}\n"
                f"**Duration:** {days} days\n"
                f"**Expires:** {expires_at.strftime('%B %d, %Y')}\n\n"
                f"✨ All {tier.lower()} features are now active!"
            ),
            color=colors.get(tier, 0x95a5a6)
        )
        
        # Tier-specific features with correct pricing
        if tier == "Pro":
            features = (
                "• Unlimited everything\n"
                "• Max 20 translation history\n" 
                "• Priority support\n"
                "• All achievements unlocked! 🏆\n"
                "• **Worth $5/month!**"
            )
        elif tier == "Premium":
            features = (
                "• Extended translation limits\n"
                "• Max 15 translation history\n"
                "• Premium support\n" 
                "• Premium achievements unlocked! 🏆\n"
                "• **Worth $3/month!**"
            )
        else:  # Basic
            features = (
                "• Basic premium features\n"
                "• Max 10 translation history\n"
                "• Basic support\n"
                "• Achievement unlocked! 🏆\n"
                "• **Worth $1/month!**"
            )
        
        embed.add_field(
            name=f"{emoji} {tier} Features Unlocked",
            value=features,
            inline=False
        )
        
        # Add upgrade path
        if tier == "Basic":
            embed.add_field(
                name="🚀 Want More?",
                value="Upgrade to Premium ($3/month) or Pro ($5/month) for even more features!",
                inline=False
            )
        elif tier == "Premium":
            embed.add_field(
                name="🚀 Want Everything?",
                value="Upgrade to Pro ($5/month) for unlimited access to all features!",
                inline=False
            )
        
        embed.add_field(
            name="🎯 What's Next?",
            value="Use `/achievements` to see your new achievements!",
            inline=False
        )
        
        await user.send(embed=embed)
        logger.info(f"✅ Notified user {user_id} about {tier} subscription")
    except Exception as notify_error:
        logger.error(f"⚠️ Couldn't notify user {user_id}: {notify_error}")

# Updated points-only notification
async def send_points_only_notification(user_id: int, points: int, amount: float):
    """Send notification for one-time point purchases"""
    try:
        user = await client.fetch_user(user_id)
        if user:
            embed = discord.Embed(
                title="💎 Points Purchased!",
                description=f"Thank you for your ${amount:.2f} donation!",
                color=0x9b59b6
            )
            embed.add_field(
                name="💰 Points Awarded",
                value=f"**{points:,} points** added to your account!",
                inline=False
            )
            embed.add_field(
                name="💰 Point Packages",
                value=(
                    "💵 **$1** = 50 points\n"
                    "💵 **$2** = 110 points *(10% bonus)*\n"
                    "💵 **$3** = 180 points *(20% bonus)*\n"
                    "💵 **$5** = 325 points *(30% bonus)*\n"
                    "💵 **$10** = 700 points *(40% bonus)*\n"
                    "💵 **$20** = 1,500 points *(50% bonus)*"
                ),
                inline=False
            )
            embed.add_field(
                name="⭐ Want Subscription Benefits?",
                value=(
                    "**Basic Tier:** $1/month - Basic features\n"
                    "**Premium Tier:** $3/month - Extended features\n"
                    "**Pro Tier:** $5/month - Unlimited everything!"
                ),
                inline=False
            )
            embed.add_field(
                name="🎯 Use Your Points",
                value="Use `/shop` to see what you can buy with points!",
                inline=False
            )
            embed.set_footer(text="💡 Subscriptions unlock features, donations give points!")
            await user.send(embed=embed)
    except Exception as e:
        logger.error(f"Failed to send points notification: {e}")

# Consolation notification for small donations
async def send_consolation_notification(user_id: int, points: int, amount: float):
    """Send notification for small donations under $1"""
    try:
        user = await client.fetch_user(user_id)
        if user:
            embed = discord.Embed(
                title="🙏 Thank You!",
                description=f"Thanks for your ${amount:.2f} donation!",
                color=0x95a5a6
            )
            embed.add_field(
                name="💝 Consolation Points",
                value=f"**{points} points** awarded as a thank you!",
                inline=False
            )
            embed.add_field(
                name="💡 How to Get More",
                value=(
                    "**For Points:** Donate $1+ one-time\n"
                    "**For Basic:** Subscribe $1/month\n"
                    "**For Premium:** Subscribe $3/month\n"
                    "**For Pro:** Subscribe $5/month"
                ),
                inline=False
            )
            embed.add_field(
                name="🎯 Your Options",
                value=(
                    "• Use `/achievements` to track progress\n"
                    "• Use `/texttr` to earn achievement points\n"
                    "• Upgrade anytime on Ko-fi!"
                ),
                inline=False
            )
            await user.send(embed=embed)
    except Exception as e:
        logger.error(f"Failed to send consolation notification: {e}")

# Language name mapping
languages = {
    "auto": "🔍 Auto-detect", 'af': 'Afrikaans', 'sq': 'Albanian', 'am': 'Amharic', 'ar': 'Arabic',
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

tesseract_lang_map = {
    "af": "afr",
    "sq": "sqi",
    "am": "amh",
    "ar": "ara",
    "hy": "hye",
    "az": "aze",
    "eu": "eus",
    "be": "bel",
    "bn": "ben",
    "bs": "bos",
    "bg": "bul",
    "ca": "cat",
    "ceb": "ceb",
    "zh-CN": "chi_sim",
    "zh-TW": "chi_tra",
    "hr": "hrv",
    "cs": "ces",
    "da": "dan",
    "nl": "nld",
    "en": "eng",
    "eo": "epo",
    "et": "est",
    "tl": "tgl",
    "fi": "fin",
    "fr": "fra",
    "fy": "fry",
    "gl": "glg",
    "ka": "kat",
    "de": "deu",
    "el": "ell",
    "gu": "guj",
    "ht": "hat",
    "hi": "hin",
    "hu": "hun",
    "is": "isl",
    "id": "ind",
    "ga": "gle",
    "it": "ita",
    "ja": "jpn",
    "kn": "kan",
    "kk": "kaz",
    "km": "khm",
    "ko": "kor",
    "ky": "kir",
    "lo": "lao",
    "la": "lat",
    "lv": "lav",
    "lt": "lit",
    "mk": "mkd",
    "ms": "msa",
    "ml": "mal",
    "mt": "mlt",
    "mr": "mar",
    "mn": "mon",
    "ne": "nep",
    "no": "nor",
    "fa": "fas",
    "pl": "pol",
    "pt": "por",
    "ro": "ron",
    "ru": "rus",
    "sk": "slk",
    "sl": "slv",
    "es": "spa",
    "sw": "swa",
    "sv": "swe",
    "ta": "tam",
    "te": "tel",
    "th": "tha",
    "tr": "tur",
    "uk": "ukr",
    "ur": "urd",
    "vi": "vie",
    "cy": "cym",
    "yi": "yid",
    "yo": "yor",
    "zu": "zul",
}

def get_display_language_name(lang_code: str, ui_lang: str = "en") -> str:
    from i18n import get_translation
    return get_translation(ui_lang, f"LANGUAGES.{lang_code}", default=lang_code)

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



async def source_language_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    current_lower = current.lower()
    matches = []
    for code, name in languages.items():
        if current_lower in code.lower() or current_lower in name.lower():
            matches.append(app_commands.Choice(name=f"{name} ({code})", value=code))
    return matches[:25]




class TierHandler:
    def __init__(self):
        self.premium_users = set()  # Premium users
        self.pro_users = set()      # Pro users          
        self.basic_users = set()    # Basic users
        self.user_tiers = {}        # Store user tier info with expiration
        self.usage_tracking = {}    # Track daily usage per user
        self.tiers = {
            'free': {
                'text_limit': 125,    # 125 characters per translation
                'voice_limit': 1800,  # 30 minutes in seconds
                'daily_translations': 10,  # Added daily translation limit
                'daily_points_min': 5,
                'daily_points_max': 10,
                'features': ['basic_translation', 'voice_chat']
            },
            'basic': {
                'text_limit': 500,    # 500 characters per translation
                'voice_limit': 3600,  # 60 minutes in seconds
                'daily_translations': 50,  # Added daily translation limit
                'daily_points_min': 10,
                'daily_points_max': 15,
                'features': ['basic_translation', 'voice_chat', 'auto_translate']
            },
            'premium': {
                'text_limit': 2000,   # 2000 characters per translation
                'voice_limit': 7200,  # 2 hours in seconds
                'daily_translations': 200,  # Added daily translation limit
                'daily_points_min': 15,
                'daily_points_max': 20,
                'features': ['basic_translation', 'voice_chat', 'auto_translate', 'enhanced_voice', 'priority_support']
            },
            'pro': {
                'text_limit': float('inf'),  # Unlimited characters
                'voice_limit': float('inf'), # Unlimited voice translation
                'daily_translations': float('inf'),  # Added unlimited daily translations
                'daily_points_min': 25,
                'daily_points_max': 35,
                'features': ['all_features', 'priority_processing', 'custom_models']
            }
        }

    def get_user_tier(self, user_id: int):
        """Get user's current tier"""
        # Check if user has a stored tier with expiration
        if user_id in self.user_tiers:
            tier_info = self.user_tiers[user_id]
            # Check if tier hasn't expired
            if 'expires' in tier_info and tier_info['expires']:
                from datetime import datetime
                if datetime.now() < tier_info['expires']:
                    return tier_info['tier']
                else:
                    # Tier expired, remove it
                    del self.user_tiers[user_id]
        
        # Check permanent tiers (highest to lowest priority)
        if hasattr(self, 'pro_users') and user_id in self.pro_users:
            return 'pro'
        elif user_id in self.premium_users:
            return 'premium'
        elif hasattr(self, 'basic_users') and user_id in self.basic_users:
            return 'basic'
        
        return 'free'

    # ORIGINAL METHODS (from your working code)
    def get_limits(self, user_id: int):
        """Get limits for a specific user"""
        tier = self.get_user_tier(user_id)
        return self.tiers.get(tier, self.tiers['free'])
    
    def get_limits_for_tier(self, tier_name: str):
        """Get limits for a specific tier by name"""
        return self.tiers.get(tier_name, self.tiers['free'])

    def set_user_tier(self, user_id: int, tier: str, expires=None):
        """Set a user's tier with optional expiration - NOT ASYNC"""
        # Remove from all permanent tier sets first
        self.premium_users.discard(user_id)
        if hasattr(self, 'pro_users'):
            self.pro_users.discard(user_id)
        if hasattr(self, 'basic_users'):
            self.basic_users.discard(user_id)
        
        if tier in ['premium', 'pro', 'basic'] and expires is None:
            # Permanent tier assignment
            if tier == 'premium':
                self.premium_users.add(user_id)
            elif tier == 'pro':
                if not hasattr(self, 'pro_users'):
                    self.pro_users = set()
                self.pro_users.add(user_id)
            elif tier == 'basic':
                if not hasattr(self, 'basic_users'):
                    self.basic_users = set()
                self.basic_users.add(user_id)
            
            # Remove from temporary tiers if exists
            if user_id in self.user_tiers:
                del self.user_tiers[user_id]
        else:
            # Temporary tier assignment
            self.user_tiers[user_id] = {
                'tier': tier,
                'expires': expires
            }
        
        return True  # Return success indicator

    async def set_user_tier_async(self, user_id: int, tier: str, expires=None):
        """Async wrapper for set_user_tier"""
        return self.set_user_tier(user_id, tier, expires)

    def get_tier_expiration(self, user_id: int):
        """Get when a user's tier expires (None if permanent or no tier)"""
        if user_id in self.user_tiers and 'expires' in self.user_tiers[user_id]:
            return self.user_tiers[user_id]['expires']
        return None

    async def get_user_tier_async(self, user_id: int):
        """Async version of get_user_tier for compatibility"""
        return self.get_user_tier(user_id)

    def add_premium_user(self, user_id: int):
        """Add a user to premium"""
        return self.set_user_tier(user_id, 'premium')

    def remove_premium_user(self, user_id: int):
        """Remove a user from premium"""
        self.premium_users.discard(user_id)
        if user_id in self.user_tiers:
            del self.user_tiers[user_id]

    def cleanup_expired_tiers(self):
        """Remove expired tiers"""
        from datetime import datetime
        expired_users = []
        
        for user_id, tier_info in self.user_tiers.items():
            if 'expires' in tier_info and tier_info['expires'] and datetime.now() >= tier_info['expires']:
                expired_users.append(user_id)
        
        for user_id in expired_users:
            del self.user_tiers[user_id]
        
        return len(expired_users)

    # NEW METHODS - Usage and Limit Checking
    def check_usage_limits(self, user_id: int, text_chars: int = 0, voice_seconds: int = 0, usage_type: str = None, amount: int = 1):
        """Check if user can perform action within limits - supports both old and new syntax"""
        from datetime import datetime, date
    
        tier = self.get_user_tier(user_id)
        limits = self.tiers[tier]
    
        # Handle old syntax (text_chars, voice_seconds parameters)
        if text_chars > 0 or voice_seconds > 0:
            # Check text limit (per translation)
            if text_chars > limits['text_limit']:
                return False, f"Text too long! {tier.title()} tier limit: {limits['text_limit']} characters per translation"
        
            # Check voice limit 
            if voice_seconds > limits['voice_limit'] and limits['voice_limit'] != float('inf'):
                return False, f"Voice limit exceeded! {tier.title()} tier limit: {limits['voice_limit']//60} minutes"
        
            return True, "Within limits"
    
        # Handle new syntax (usage_type parameter)
        if usage_type:
            # Initialize usage tracking for user if not exists
            today = date.today().isoformat()
            if user_id not in self.usage_tracking:
                self.usage_tracking[user_id] = {}
            if today not in self.usage_tracking[user_id]:
                self.usage_tracking[user_id][today] = {
                    'translations': 0,
                    'voice_seconds': 0,
                    'text_characters': 0
                }
        
            daily_usage = self.usage_tracking[user_id][today]
        
            # Check limits based on usage type
            if usage_type == 'text_characters':
                if amount > limits['text_limit']:
                    return False, f"Text too long (limit: {limits['text_limit']} characters)"
        
            elif usage_type == 'voice_seconds':
                if daily_usage['voice_seconds'] + amount > limits['voice_limit']:
                    return False, f"Daily voice limit reached ({limits['voice_limit']//60} minutes)"
    
        return True, "OK"


    def add_usage(self, user_id: int, usage_type: str, amount: int):
        """Add usage for a user"""
        from datetime import date
        
        today = date.today().isoformat()
        if user_id not in self.usage_tracking:
            self.usage_tracking[user_id] = {}
        if today not in self.usage_tracking[user_id]:
            self.usage_tracking[user_id][today] = {
                'translations': 0,
                'voice_seconds': 0,
                'text_characters': 0
            }
        
        if usage_type in self.usage_tracking[user_id][today]:
            self.usage_tracking[user_id][today][usage_type] += amount

    def get_usage_stats(self, user_id: int):
        """Get current usage stats for a user"""
        from datetime import date
        
        today = date.today().isoformat()
        if (user_id not in self.usage_tracking or 
            today not in self.usage_tracking[user_id]):
            return {
                'translations': 0,
                'voice_seconds': 0,
                'text_characters': 0
            }
        
        return self.usage_tracking[user_id][today].copy()

    def get_remaining_limits(self, user_id: int):
        """Get remaining limits for a user"""
        tier = self.get_user_tier(user_id)
        limits = self.tiers[tier]
        usage = self.get_usage_stats(user_id)
        
        remaining = {}
        for key in ['translations', 'voice_seconds']:
            if limits.get(f'daily_{key}', float('inf')) == float('inf'):
                remaining[key] = float('inf')
            else:
                limit_key = f'daily_{key}' if key == 'translations' else 'voice_limit'
                remaining[key] = max(0, limits[limit_key] - usage.get(key, 0))
        
        remaining['text_limit'] = limits['text_limit']
        return remaining

    def has_feature(self, user_id: int, feature: str):
        """Check if user has access to a specific feature"""
        tier = self.get_user_tier(user_id)
        features = self.tiers[tier].get('features', [])
        return feature in features or 'all_features' in features

    # Tier Management Methods
    def add_pro_user(self, user_id: int):
        """Add a user to pro"""
        return self.set_user_tier(user_id, 'pro')

    def remove_pro_user(self, user_id: int):
        """Remove a user from pro"""
        if hasattr(self, 'pro_users'):
            self.pro_users.discard(user_id)
        if user_id in self.user_tiers:
            del self.user_tiers[user_id]

    def add_basic_user(self, user_id: int):
        """Add a user to basic"""
        return self.set_user_tier(user_id, 'basic')

    def remove_basic_user(self, user_id: int):
        """Remove a user from basic"""
        if hasattr(self, 'basic_users'):
            self.basic_users.discard(user_id)
        if user_id in self.user_tiers:
            del self.user_tiers[user_id]

    def cleanup_old_usage(self, days_to_keep: int = 7):
        """Clean up old usage data"""
        from datetime import date, timedelta
        
        cutoff_date = (date.today() - timedelta(days=days_to_keep)).isoformat()
        cleaned_count = 0
        
        for user_id in list(self.usage_tracking.keys()):
            user_usage = self.usage_tracking[user_id]
            dates_to_remove = [d for d in user_usage.keys() if d < cutoff_date]
            
            for date_str in dates_to_remove:
                del user_usage[date_str]
                cleaned_count += 1
            
            # Remove user entry if no usage data left
            if not user_usage:
                del self.usage_tracking[user_id]
        
        return cleaned_count

    def get_tier_info(self, tier_name: str):
        """Get complete information about a tier"""
        if tier_name not in self.tiers:
            return None
        
        tier_data = self.tiers[tier_name].copy()
        
        # Format limits for display
        if tier_data['text_limit'] == float('inf'):
            tier_data['text_limit_display'] = "Unlimited"
        else:
            tier_data['text_limit_display'] = f"{tier_data['text_limit']:,} characters"
        
        if tier_data['voice_limit'] == float('inf'):
            tier_data['voice_limit_display'] = "Unlimited"
        else:
            tier_data['voice_limit_display'] = f"{tier_data['voice_limit']//60} minutes"
        
        if tier_data['daily_translations'] == float('inf'):
            tier_data['translations_display'] = "Unlimited"
        else:
            tier_data['translations_display'] = f"{tier_data['daily_translations']} per day"
        
        return tier_data

    def get_user_stats(self, user_id: int):
        """Get comprehensive user statistics"""
        tier = self.get_user_tier(user_id)
        limits = self.get_limits(user_id)
        usage = self.get_usage_stats(user_id)
        remaining = self.get_remaining_limits(user_id)
        expiration = self.get_tier_expiration(user_id)
        
        return {
            'user_id': user_id,
            'tier': tier,
            'limits': limits,
            'usage': usage,
            'remaining': remaining,
            'expiration': expiration,
            'features': limits.get('features', [])
        }

    # Tier Status Check Methods
    def is_premium(self, user_id: int):
        """Check if user has premium or higher tier"""
        tier = self.get_user_tier(user_id)
        return tier in ['premium', 'pro']

    def is_pro(self, user_id: int):
        """Check if user has pro tier"""
        return self.get_user_tier(user_id) == 'pro'

    def is_basic(self, user_id: int):
        """Check if user has basic or higher tier"""
        tier = self.get_user_tier(user_id)
        return tier in ['basic', 'premium', 'pro']

    def get_all_premium_users(self):
        """Get all users with premium or higher access"""
        all_premium = set(self.premium_users)
        if hasattr(self, 'pro_users'):
            all_premium.update(self.pro_users)
        
        # Add temporary premium/pro users
        from datetime import datetime
        for user_id, tier_info in self.user_tiers.items():
            if (tier_info['tier'] in ['premium', 'pro'] and
                ('expires' not in tier_info or not tier_info['expires'] or
                 datetime.now() < tier_info['expires'])):
                all_premium.add(user_id)
        
        return all_premium

    def get_tier_counts(self):
        """Get count of users in each tier"""
        from datetime import datetime
        
        counts = {'free': 0, 'basic': 0, 'premium': 0, 'pro': 0}
        
        # Count permanent users
        counts['premium'] += len(self.premium_users)
        if hasattr(self, 'pro_users'):
            counts['pro'] += len(self.pro_users)
        if hasattr(self, 'basic_users'):
            counts['basic'] += len(self.basic_users)
        
        # Count temporary users
        for user_id, tier_info in self.user_tiers.items():
            tier = tier_info['tier']
            if ('expires' not in tier_info or not tier_info['expires'] or
                datetime.now() < tier_info['expires']):
                if tier in counts:
                    counts[tier] += 1
        
        return counts

    def upgrade_user_tier(self, user_id: int, new_tier: str, expires=None):
        """Upgrade a user to a higher tier (with validation)"""
        current_tier = self.get_user_tier(user_id)
        tier_hierarchy = ['free', 'basic', 'premium', 'pro']
        
        current_level = tier_hierarchy.index(current_tier) if current_tier in tier_hierarchy else 0
        new_level = tier_hierarchy.index(new_tier) if new_tier in tier_hierarchy else 0
        
        if new_level <= current_level:
            return False, f"Cannot downgrade from {current_tier} to {new_tier}"
        
        return self.set_user_tier(user_id, new_tier, expires), f"Upgraded from {current_tier} to {new_tier}"

    def downgrade_user_tier(self, user_id: int, new_tier: str):
        """Downgrade a user to a lower tier"""
        current_tier = self.get_user_tier(user_id)
        
        # Remove from all permanent tiers
        self.premium_users.discard(user_id)
        if hasattr(self, 'pro_users'):
            self.pro_users.discard(user_id)
        if hasattr(self, 'basic_users'):
            self.basic_users.discard(user_id)
        
        # Remove from temporary tiers
        if user_id in self.user_tiers:
            del self.user_tiers[user_id]
        
        # Set new tier if not free
        if new_tier != 'free':
            self.set_user_tier(user_id, new_tier)
        
        return True, f"Downgraded from {current_tier} to {new_tier}"

    def extend_user_tier(self, user_id: int, additional_days: int):
        """Extend a user's current tier by additional days"""
        from datetime import datetime, timedelta
        
        current_tier = self.get_user_tier(user_id)
        if current_tier == 'free':
            return False, "Cannot extend free tier"
        
        # Check if user has permanent tier
        if (user_id in self.premium_users or
            (hasattr(self, 'pro_users') and user_id in self.pro_users) or
            (hasattr(self, 'basic_users') and user_id in self.basic_users)):
            return False, f"User already has permanent {current_tier} tier"
        
        # Get current expiration or set to now
        current_expiry = self.get_tier_expiration(user_id)
        if current_expiry:
            new_expiry = current_expiry + timedelta(days=additional_days)
        else:
            new_expiry = datetime.now() + timedelta(days=additional_days)
        
        # Update the tier with new expiration
        self.user_tiers[user_id] = {
            'tier': current_tier,
            'expires': new_expiry
        }
        
        return True, f"Extended {current_tier} tier by {additional_days} days"

    def get_tier_revenue_info(self):
        """Get revenue information for all tiers (for analytics)"""
        tier_prices = {
            'basic': 1.0,    # $1/month
            'premium': 3.0,  # $3/month  
            'pro': 5.0      # $5/month
        }
        
        counts = self.get_tier_counts()
        revenue_info = {}
        
        for tier, count in counts.items():
            if tier in tier_prices:
                revenue_info[tier] = {
                    'users': count,
                    'monthly_revenue': count * tier_prices[tier],
                    'price_per_user': tier_prices[tier]
                }
        
        total_revenue = sum(info['monthly_revenue'] for info in revenue_info.values())
        total_paid_users = sum(info['users'] for info in revenue_info.values())
        
        revenue_info['totals'] = {
            'paid_users': total_paid_users,
            'free_users': counts['free'],
            'monthly_revenue': total_revenue,
            'average_revenue_per_user': total_revenue / max(total_paid_users, 1)
        }
        
        return revenue_info

    def bulk_tier_operation(self, user_ids: list, operation: str, tier: str = None, days: int = None):
        """Perform bulk operations on multiple users"""
        from datetime import datetime, timedelta
        
        results = {'success': [], 'failed': []}
        
        for user_id in user_ids:
            try:
                if operation == 'upgrade' and tier:
                    success, message = self.upgrade_user_tier(user_id, tier,
                        datetime.now() + timedelta(days=days) if days else None)
                elif operation == 'downgrade' and tier:
                    success, message = self.downgrade_user_tier(user_id, tier)
                elif operation == 'extend' and days:
                    success, message = self.extend_user_tier(user_id, days)
                elif operation == 'remove':
                    success, message = self.downgrade_user_tier(user_id, 'free')
                else:
                    success, message = False, "Invalid operation"
                
                if success:
                    results['success'].append({'user_id': user_id, 'message': message})
                else:
                    results['failed'].append({'user_id': user_id, 'error': message})
                
            except Exception as e:
                results['failed'].append({'user_id': user_id, 'error': str(e)})
        
        return results

    def get_expiring_users(self, days_ahead: int = 7):
        """Get users whose tiers will expire within specified days"""
        from datetime import datetime, timedelta
        
        expiring_soon = []
        cutoff_date = datetime.now() + timedelta(days=days_ahead)
        
        for user_id, tier_info in self.user_tiers.items():
            if ('expires' in tier_info and tier_info['expires'] and
                datetime.now() < tier_info['expires'] <= cutoff_date):
                
                days_remaining = (tier_info['expires'] - datetime.now()).days
                expiring_soon.append({
                    'user_id': user_id,
                    'tier': tier_info['tier'],
                    'expires': tier_info['expires'],
                    'days_remaining': days_remaining
                })
        
        return sorted(expiring_soon, key=lambda x: x['expires'])

    def validate_tier_integrity(self):
        """Validate and fix any tier data inconsistencies"""
        from datetime import datetime
        
        issues_found = []
        fixes_applied = []
        
        # Check for expired tiers
        expired_count = self.cleanup_expired_tiers()
        if expired_count > 0:
            fixes_applied.append(f"Cleaned up {expired_count} expired tiers")
        
        # Check for users in multiple permanent tier sets
        all_users = set()
        for tier_set_name in ['premium_users', 'pro_users', 'basic_users']:
            if hasattr(self, tier_set_name):
                tier_set = getattr(self, tier_set_name)
                overlapping = all_users.intersection(tier_set)
                if overlapping:
                    issues_found.append(f"Users in multiple permanent tiers: {overlapping}")
                all_users.update(tier_set)
        
        # Check for users in both permanent and temporary tiers
        permanent_users = all_users
        temporary_users = set(self.user_tiers.keys())
        overlapping = permanent_users.intersection(temporary_users)
        
        if overlapping:
            issues_found.append(f"Users in both permanent and temporary tiers: {overlapping}")
            # Fix by removing from temporary (permanent takes precedence)
            for user_id in overlapping:
                del self.user_tiers[user_id]
            fixes_applied.append(f"Fixed {len(overlapping)} users with conflicting tier assignments")
        
        return {
            'issues_found': issues_found,
            'fixes_applied': fixes_applied,
            'integrity_status': 'CLEAN' if not issues_found else 'ISSUES_FIXED'
        }

    def export_tier_data(self):
        """Export all tier data for backup/analysis"""
        from datetime import datetime
        
        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'permanent_tiers': {
                'premium_users': list(self.premium_users),
                'pro_users': list(getattr(self, 'pro_users', set())),
                'basic_users': list(getattr(self, 'basic_users', set()))
            },
            'temporary_tiers': {},
            'tier_definitions': self.tiers,
            'usage_tracking': self.usage_tracking
        }
        
        # Convert datetime objects to ISO strings for JSON serialization
        for user_id, tier_info in self.user_tiers.items():
            export_tier_info = tier_info.copy()
            if 'expires' in export_tier_info and export_tier_info['expires']:
                export_tier_info['expires'] = export_tier_info['expires'].isoformat()
            export_data['temporary_tiers'][str(user_id)] = export_tier_info
        
        return export_data

    def import_tier_data(self, import_data):
        """Import tier data from backup"""
        from datetime import datetime
        
        try:
            # Import permanent tiers
            if 'permanent_tiers' in import_data:
                self.premium_users = set(import_data['permanent_tiers'].get('premium_users', []))
                self.pro_users = set(import_data['permanent_tiers'].get('pro_users', []))
                self.basic_users = set(import_data['permanent_tiers'].get('basic_users', []))
            
            # Import temporary tiers
            if 'temporary_tiers' in import_data:
                self.user_tiers = {}
                for user_id_str, tier_info in import_data['temporary_tiers'].items():
                    user_id = int(user_id_str)
                    imported_tier_info = tier_info.copy()
                    
                    # Convert ISO string back to datetime
                    if 'expires' in imported_tier_info and imported_tier_info['expires']:
                        imported_tier_info['expires'] = datetime.fromisoformat(imported_tier_info['expires'])
                    
                    self.user_tiers[user_id] = imported_tier_info
            
            # Import usage tracking if available
            if 'usage_tracking' in import_data:
                self.usage_tracking = import_data['usage_tracking']
            
            return True, "Tier data imported successfully"
            
        except Exception as e:
            return False, f"Failed to import tier data: {str(e)}"
    def get_tier_type_from_reward_id(self, reward_id: str) -> str | None:
        """
        Map a reward_id like 'temp_pro_1d' to the tier type ('pro', 'premium', 'basic').
        Returns None if reward_id does not correspond to a tier.
        """
        # This assumes your reward IDs start with 'temp_{tier}_...'
        if reward_id.startswith('temp_pro'):
            return 'pro'
        elif reward_id.startswith('temp_premium'):
            return 'premium'
        elif reward_id.startswith('temp_basic'):
            return 'basic'
        else:
            return None

    async def upgrade_user_tier(self, user_id: int, reward_id: str, expires_at):
        """
        Upgrade the user tier based on reward_id, with expiration.
        Returns (success: bool, message: str)
        """
        tier_type = self.get_tier_type_from_reward_id(reward_id)
        if tier_type is None:
            return False, f"Reward '{reward_id}' is not a tier upgrade."

        # Set the user tier with expiration
        success = self.set_user_tier(user_id, tier_type, expires_at)
        if success:
            return True, f"User upgraded to {tier_type.title()} tier until {expires_at.strftime('%Y-%m-%d %H:%M:%S')}"
        else:
            return False, "Failed to upgrade user tier."

# Update tier_handler instance
tier_handler = TierHandler()


# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
NGROK_TOKEN = os.getenv('NGROK_TOKEN')
tier_handler = TierHandler()
if hasattr(tier_handler.premium_users, 'add'):
    # It's a set
    tier_handler.premium_users.add(1192196672437096520)
else:
    # It's a dict, so use dict assignment
    tier_handler.premium_users[1192196672437096520] = True
# Session tracking for commands and usage
user_sessions = {}  # Track user sessions for point awarding

async def track_command_usage(interaction: discord.Interaction):
    """Track command usage for point awarding"""
    user_id = interaction.user.id
    
    # Initialize session if needed
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            'active': True,
            'commands_used': 0,
            'session_start': datetime.now()
        }
        reward_db.increment_session_count(user_id)
    
    # Increment command usage
    user_sessions[user_id]['commands_used'] += 1
    
    # Award small points for command usage (except for reward system commands to prevent farming)
    if interaction.command.name not in ['daily', 'shop', 'buy', 'profile', 'leaderboard', 'transactions', 'achievements', 'rewards']:
        reward_db.add_points(user_id, 1, f"Command usage: {interaction.command.name}")

async def award_usage_points():
    """Background task to award points for active usage"""
    while True:
        try:
            for user_id, session_data in user_sessions.items():
                if session_data.get('active', False):
                    is_premium = user_id in tier_handler.premium_users
                    points_to_award = 10 if is_premium else 1
                    
                    reward_db.add_points(user_id, points_to_award, "Hourly usage reward")
                    reward_db.update_usage_time(user_id, 1.0)  # 1 hour
            
            # Clean up expired rewards
            reward_db.cleanup_expired_rewards()
            
        except Exception as e:
            logger.error(f"Error in background point awarding: {e}")
        
        # Wait 1 hour before next award
        await asyncio.sleep(3600)

async def track_command_usage(interaction: discord.Interaction):
    """Track command usage for point awarding"""
    user_id = interaction.user.id
    
    # Initialize session if needed
    if user_id not in user_sessions:
        user_sessions[user_id] = {
            'active': True,
            'commands_used': 0,
            'session_start': datetime.now()
        }
        reward_db.increment_session_count(user_id)
    
    # Increment command usage
    user_sessions[user_id]['commands_used'] += 1
    
    # Award small points for command usage
    reward_db.add_points(user_id, 1, f"Command usage: {interaction.command.name}")
def has_enhanced_voice_access(user_id: int, reward_db, tier_handler) -> bool:
    """Check if user has access to Enhanced Voice V2"""
    # Premium users always have access
    if user_id in tier_handler.premium_users:
        return True
    
    # Check for active enhanced voice reward
    return reward_db.has_active_reward(user_id, 'enhanced_voice')

def get_effective_limits(user_id: int, tier_handler, reward_db):
    """Get user's effective limits including active rewards"""
    base_limits = tier_handler.get_limits(user_id)
    
    # Check for active limit boosts
    if reward_db.has_active_reward(user_id, 'unlimited_text'):
        base_limits['text_limit'] = float('inf')
    
    if reward_db.has_active_reward(user_id, 'extended_voice'):
        base_limits['voice_limit'] = 1800  # 30 minutes
    
    if reward_db.has_active_reward(user_id, 'temp_premium'):
        base_limits['text_limit'] = float('inf')
        base_limits['voice_limit'] = float('inf')
    
    return base_limits
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

class TranslationServer:
    def __init__(self):
        # Single tunnel for all users
        self.main_tunnel = ngrok.connect(5000, "http", name="main")
        self.public_url = self.main_tunnel.public_url
        print(f"🌐 Main Ngrok URL: {self.public_url}")
        
        # Store user sessions
        self.translators = {}
        
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

@tree.command(name="help", description="List of commands for your personal translation bot")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def start(interaction: discord.Interaction):
    try:
        user_id = interaction.user.id
        ui_lang = await get_user_ui_language(user_id)

        # Track usage
        try:
            await track_command_usage(interaction)
        except Exception as e:
            print(f"track_command_usage error: {e}")

        guild_id = interaction.guild_id

        user_data = reward_db.get_or_create_user(user_id, interaction.user.display_name)
        is_new_user = user_data['total_sessions'] == 1

        if guild_id:
            translation_server.translators = getattr(translation_server, 'translators', {})
            translation_server.translators.setdefault(guild_id, {}).setdefault(user_id, {})
            try:
                translation_server.get_user_url(user_id)
            except Exception as e:
                print(f"URL init fail: {e}")

        try:
            current_tier = tier_handler.get_user_tier(user_id)
            limits = tier_handler.get_limits(user_id)
        except:
            current_tier = 'free'
            limits = {'text_limit': 50, 'voice_limit': 1800}

        # Hardcoded tier colors here
        tier_colors = {
            'free': 0x95a5a6,      # grey
            'basic': 0x3498db,     # blue
            'premium': 0xe67e22,   # orange
            'pro': 0x9b59b6        # purple
        }

        tier_info = {
            'name': current_tier.title(),
            'emoji': TIER_EMOJIS.get(current_tier, '🆓'),
            'color': tier_colors.get(current_tier, 0x95a5a6),
            'point_multiplier': {
                'free': '1x', 'basic': '1.5x', 'premium': '2x', 'pro': '3x'
            }.get(current_tier, '1x')
        }

        embed = discord.Embed(
            title=get_translation(ui_lang, "START.new_user_title" if is_new_user else "START.returning_user_title", emoji=tier_info['emoji']),
            description=get_translation(ui_lang, "START.new_user_description" if is_new_user else "START.returning_user_description", username=interaction.user.display_name),
            color=tier_info['color'] 
        )

        text_limit_str = get_translation(ui_lang, "START.tier_unlimited") if limits['text_limit'] == float('inf') else str(limits['text_limit'])
        voice_limit_str = get_translation(ui_lang, "START.tier_unlimited") if limits['voice_limit'] == float('inf') else str(limits['voice_limit']//60)

        embed.add_field(
            name=get_translation(ui_lang, "START.tier_field_name", tier=tier_info['name']),
            value=get_translation(ui_lang, "START.tier_field_value", text_limit=text_limit_str, voice_limit=voice_limit_str, points=f"{user_data['points']:,}"),
            inline=False
        )

        if current_tier == 'free':
            embed.add_field(
                name=get_translation(ui_lang, "START.upgrade_benefits_name"),
                value=get_translation(ui_lang, "START.upgrade_benefits_value"),
                inline=False
            )
        else:
            embed.add_field(
                name=get_translation(ui_lang, "START.premium_active_name"),
                value=get_translation(ui_lang, "START.premium_active_value", text_limit=text_limit_str, voice_limit=voice_limit_str, multiplier=tier_info['point_multiplier']),
                inline=False
            )

        if interaction.guild:
            perms = interaction.channel.permissions_for(interaction.user)
            if perms.administrator or perms.manage_guild:
                embed.add_field(
                    name=get_translation(ui_lang, "START.admin_tips_name"),
                    value=get_translation(ui_lang, "START.admin_tips_value"),
                    inline=False
                )

        from datetime import datetime
        today = datetime.now().date().isoformat()
        if user_data.get('last_daily_claim') != today:
            embed.add_field(
                name=get_translation(ui_lang, "START.daily_available_name"),
                value=get_translation(ui_lang, "START.daily_available_value"),
                inline=True
            )
        else:
            embed.add_field(
                name=get_translation(ui_lang, "START.daily_claimed_name"),
                value=get_translation(ui_lang, "START.daily_claimed_value"),
                inline=True
            )

        if interaction.guild:
            embed.add_field(
                name=get_translation(ui_lang, "START.stats_name"),
                value=get_translation(ui_lang, "START.stats_value", points=f"{user_data['points']:,}", sessions=user_data['total_sessions'], usage=f"{user_data['total_usage_hours']:.1f}", tier=tier_info['name']),
                inline=True
            )

        # Command categories
        embed.add_field(
            name=get_translation(ui_lang, "START.voice_commands_name"),
            value=get_translation(ui_lang, "START.voice_commands_value"),
            inline=False
        )
        embed.add_field(
            name=get_translation(ui_lang, "START.text_commands_name"),
            value=get_translation(ui_lang, "START.text_commands_value"),
            inline=False
        )
        embed.add_field(
            name=get_translation(ui_lang, "HELP.readimage_title"),
            value=get_translation(ui_lang, "HELP.readimage_value"),
            inline=False
        )

        embed.add_field(
            name=get_translation(ui_lang, "START.achievements_name"),
            value=get_translation(ui_lang, "START.achievements_value"),
            inline=False
        )
        embed.add_field(
            name=get_translation(ui_lang, "HELP.settings_title"),
            value=get_translation(ui_lang, "HELP.settings_value"),
            inline=False
        )
        embed.add_field(
            name=get_translation(ui_lang, "HELP.social_title"),
            value=get_translation(ui_lang, "HELP.social_value"),
            inline=False
        )
        setup_key = "HELP.setup_value_admin" if (interaction.guild and (perms.administrator or perms.manage_guild)) else "HELP.setup_value_user"
        embed.add_field(
            name=get_translation(ui_lang, "HELP.setup_title"),
            value=get_translation(ui_lang, setup_key),
            inline=False
        )
        embed.add_field(
            name=get_translation(ui_lang, "HELP.info_title"),
            value=get_translation(ui_lang, "HELP.info_value"),
            inline=False
        )
        embed.add_field(
            name=get_translation(ui_lang, "HELP.context_title"),
            value=get_translation(ui_lang, "HELP.context_value"),
            inline=False
        )
        embed.add_field(
            name=get_translation(ui_lang, "HELP.tips_title"),
            value=get_translation(ui_lang, "HELP.tips_value"),
            inline=False
        )

        embed.add_field(
            name=get_translation(ui_lang, "START.language_format_name"),
            value=get_translation(ui_lang, "START.language_format_value"),
            inline=False
        )

        if interaction.guild:
            embed.set_footer(text=get_translation(ui_lang, "HELP.footer_server", server=interaction.guild.name))
        else:
            embed.set_footer(text=get_translation(ui_lang, "HELP.footer_dm"))

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        import traceback
        print(f"Unhandled error: {e}\n{traceback.format_exc()}")
        fallback_lang = await get_user_ui_language(interaction.user.id) if interaction.user else 'en'
        msg = get_translation(fallback_lang, "START.error_critical", error=str(e))
        if not interaction.response.is_done():
            await interaction.response.send_message(msg, ephemeral=True)
        else:
            await interaction.followup.send(msg, ephemeral=True)

@tree.command(
    name="setchannel",
    description="Restrict or allow translation in specific text/voice channels and languages (admin/mod only)"
)
@app_commands.describe(
    channel="Text or voice channel to restrict",
    channel_type="Type of channel: text, voice, or both",
    mode="Choose 'allow' to only allow listed languages, or 'block' to block listed languages",
    languages="Comma-separated language codes or names (e.g. 'en, es', or 'English, Spanish')"
)
@app_commands.default_permissions(manage_guild=True)
@app_commands.checks.has_permissions(manage_guild=True)
async def set_channel(
    interaction: discord.Interaction,
    channel: discord.abc.GuildChannel,
    channel_type: str,
    mode: str,
    languages: str
):
    user_id = interaction.user.id
    ui_lang = await get_user_ui_language(user_id)
    

    if not interaction.guild:
        await interaction.response.send_message(
            get_translation(ui_lang, "SETCHANNEL.error_server_only"),
            ephemeral=True
        )
        return

    perms = interaction.guild.get_member(interaction.user.id).guild_permissions
    if not (perms.administrator or perms.manage_guild):
        await interaction.response.send_message(
            get_translation(ui_lang, "SETCHANNEL.error_no_permission"),
            ephemeral=True
        )
        return

    if channel_type not in ["text", "voice", "both"]:
        await interaction.response.send_message(
            get_translation(ui_lang, "SETCHANNEL.error_invalid_channel_type"),
            ephemeral=True
        )
        return

    if mode not in ["allow", "block"]:
        await interaction.response.send_message(
            get_translation(ui_lang, "SETCHANNEL.error_invalid_mode"),
            ephemeral=True
        )
        return

    if not languages or not languages.strip():
        await interaction.response.send_message(
            get_translation(ui_lang, "SETCHANNEL.error_no_languages"),
            ephemeral=True
        )
        return

    guild_id = interaction.guild.id
    languages_clean = languages.strip().lower()

    # 🔁 Unified name/code conversion using get_language_code
    def names_to_codes(lang_names):
        codes = set()
        for name in lang_names:
            code = get_language_code(name)
            if code:
                codes.add(code)
        return codes

    # 🚧 Apply restriction logic
    async def apply_restriction(chan_type):
        if languages_clean == "none":
            await db.set_channel_restriction(guild_id, channel.id, chan_type, set(), block_all=True)
            return get_translation(ui_lang, "SETCHANNEL.blocked_all",
                                   channel_type=chan_type, channel_id=channel.id)
        elif languages_clean == "all":
            await db.set_channel_restriction(guild_id, channel.id, chan_type, set(), block_all=False)
            return get_translation(ui_lang, "SETCHANNEL.allowed_all",
                                   channel_id=channel.id, channel_type=chan_type)
        else:
            lang_inputs = [l.strip() for l in languages.split(",") if l.strip()]
            lang_codes = names_to_codes(lang_inputs)
            if not lang_codes:
                return get_translation(ui_lang, "SETCHANNEL.error_no_valid_languages")

            await db.set_channel_restriction(guild_id, channel.id, chan_type, lang_codes, block_all=False)

            lang_display = ", ".join(lang_inputs)
            if mode == "allow":
                return get_translation(ui_lang, "SETCHANNEL.allowed_specific",
                                       channel_id=channel.id, channel_type=chan_type, languages=lang_display)
            else:
                return get_translation(ui_lang, "SETCHANNEL.blocked_specific",
                                       channel_id=channel.id, channel_type=chan_type, languages=lang_display)

    if channel_type == "both":
        results = [await apply_restriction(t) for t in ["text", "voice"]]
        await interaction.response.send_message("\n".join(results), ephemeral=True)
    else:
        result = await apply_restriction(channel_type)
        await interaction.response.send_message(result, ephemeral=True)
async def language_name_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    user_id = interaction.user.id
    ui_lang = await get_user_ui_language(user_id)
    current_lower = current.lower()
    matches = []

    # Check language names translated into user's UI language
    for code, name in languages.items():
        translated_name = get_translation(ui_lang, f"LANGUAGES.{code}", default=name)
        # Match if input matches part of translated name or code
        if current_lower in translated_name.lower() or current_lower in code.lower():
            matches.append(app_commands.Choice(
                name=f"{translated_name} ({code})",  # What user sees
                value=code                           # What the command receives
            ))

    # Add special options with translations
    if "all".startswith(current_lower):
        matches.insert(0, app_commands.Choice(
            name=get_translation(ui_lang, "SETCHANNEL.autocomplete_all", default="All Languages"),
            value="all"
        ))
    if "none".startswith(current_lower):
        matches.insert(0, app_commands.Choice(
            name=get_translation(ui_lang, "SETCHANNEL.autocomplete_none", default="Block All Languages"),
            value="none"
        ))

    return matches[:25]

# Link autocomplete to set_channel command parameter
set_channel.autocomplete('languages')(language_name_autocomplete)


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
    ui_lang = await get_user_ui_language(user_id)
    await db.get_or_create_user(user_id, interaction.user.display_name)

    # Use the same tier detection logic as autotranslate command
    tier = tier_handler.get_user_tier(user_id)
    is_premium = tier in ['premium', 'pro']
    limits = tier_handler.get_limits(user_id)

    source_code = "auto" if source_lang.lower() == "auto" else get_language_code(source_lang)
    target_code = get_language_code(target_lang)

    if target_code == "auto":
        await interaction.response.send_message(
            get_translation(ui_lang, "AUTO.error_auto_not_allowed_for_target"),
            ephemeral=True
        )
        return

    if interaction.guild:
        allowed = await db.is_translation_allowed(
            interaction.guild.id,
            interaction.channel.id,
            "text",
            target_code
        )
        if not allowed:
            await interaction.response.send_message(
                get_translation(ui_lang, "TEXTTR.error_language_not_allowed"),
                ephemeral=True
            )
            return

    if not source_code:
        await interaction.response.send_message(
            get_translation(ui_lang, "TEXTTR.error_invalid_source", language=source_lang),
            ephemeral=True
        )
        return

    if not target_code:
        await interaction.response.send_message(
            get_translation(ui_lang, "TEXTTR.error_invalid_target", language=target_lang),
            ephemeral=True
        )
        return

    if len(text) > limits['text_limit']:
        await interaction.response.send_message(
            get_translation(ui_lang, "TEXTTR.error_text_too_long", tier=tier, limit=limits['text_limit']),
            ephemeral=True
        )
        return

    await interaction.response.defer(ephemeral=False)

    try:
        translator = GoogleTranslator(source=source_code, target=target_code)
        translated = translator.translate(text)

        points_map = {'free': 1, 'basic': 2, 'premium': 3, 'pro': 4}
        points_awarded = points_map[tier]
        reward_db.add_points(user_id, points_awarded, f"Text translation: {source_code}→{target_code}")

        await db.track_usage(user_id, text_chars=len(text))
        await db.save_translation(
            user_id=user_id,
            guild_id=interaction.guild_id or 0,
            original_text=text,
            translated_text=translated,
            source_lang=source_code,
            target_lang=target_code,
            translation_type="text"
        )

        achievement_db.track_translation(user_id, source_code, target_code, is_premium)
        new_achievements = achievement_db.check_achievements(user_id)
        if new_achievements:
            await send_achievement_notification(client, user_id, new_achievements)

        await safe_track_translation_achievement(
            user_id=user_id,
            username=interaction.user.display_name,
            source_lang=source_code,
            target_lang=target_code
        )

        uncashed_points, _ = reward_db.get_uncashed_achievement_points(user_id)
        await notify_uncashed_achievements(user_id, interaction.user.display_name, uncashed_points)

        # Create and send the translation embeds
        await create_and_send_translation_embeds(
            interaction=interaction,
            original_text=text,
            translated_text=translated,
            source_code=source_code,
            target_code=target_code,
            tier=tier,
            points_awarded=points_awarded,
            limits=limits,
            ui_lang=ui_lang,
            user_id=user_id
        )

    except Exception as e:
        await interaction.followup.send(
            get_translation(ui_lang, "TEXTTR.error_translation_failed", error=str(e)),
            ephemeral=True
        )


async def create_and_send_translation_embeds(
    interaction: discord.Interaction,
    original_text: str,
    translated_text: str,
    source_code: str,
    target_code: str,
    tier: str,
    points_awarded: int,
    limits: dict,
    ui_lang: str,
    user_id: int
):
    """Create and send translation embeds with proper truncation and splitting"""
    
    # Get language names and flags
    source_name = get_translation(ui_lang, f"LANGUAGES.{source_code}", default=languages.get(source_code, source_code))
    target_name = get_translation(ui_lang, f"LANGUAGES.{target_code}", default=languages.get(target_code, target_code))
    source_flag = flag_mapping.get(source_code, '🌐')
    target_flag = flag_mapping.get(target_code, '🌐')
    
    # Use the same tier colors as autotranslate command
    tier_colors = {'free': 0x95a5a6, 'basic': 0x3498db, 'premium': 0xf39c12, 'pro': 0x9b59b6}
    embed_color = tier_colors.get(tier, discord.Color.greyple())
    
    # Calculate footer text
    if tier == 'free':
        footer_text = get_translation(ui_lang, "TEXTTR.footer_free", current=len(original_text), limit=limits['text_limit'])
    elif tier == 'basic':
        footer_text = get_translation(ui_lang, "TEXTTR.footer_basic", current=len(original_text), limit=limits['text_limit'])
    elif tier == 'premium':
        footer_text = get_translation(ui_lang, "TEXTTR.footer_premium")
    else:  # pro tier
        footer_text = get_translation(ui_lang, "TEXTTR.footer_pro")

    if interaction.guild:
        footer_text += " " + get_translation(ui_lang, "TEXTTR.footer_server", server=interaction.guild.name)
    else:
        footer_text += " " + get_translation(ui_lang, "TEXTTR.footer_dm")
    
    footer_text = footer_text[:2048]  # Discord footer limit
    
    # Field names (truncated to Discord's 256 character limit)
    original_field_name = get_translation(ui_lang, "TEXTTR.original_field", flag=source_flag, language=source_name)[:256]
    translation_field_name = get_translation(ui_lang, "TEXTTR.translation_field", flag=target_flag, language=target_name)[:256]
    points_field_name = get_translation(ui_lang, "TEXTTR.points_field")[:256]
    points_field_value = get_translation(ui_lang, "TEXTTR.points_value", points=points_awarded)[:1024]
    
    # Helper function to add field and handle embed limits
    def add_field_to_embed(embed_obj, field_name, field_value, field_counter):
        """Helper function to add field and handle embed limits"""
        # Check if current embed can hold another field (Discord limit is 25 fields per embed)
        if field_counter >= 25:
            return None, field_counter  # Signal that we need a new embed
        
        embed_obj.add_field(
            name=field_name,
            value=field_value,
            inline=False
        )
        return embed_obj, field_counter + 1
    
    # Split texts into chunks that fit Discord's 1024 character field limit
    def split_text_for_fields(text, max_length=1020):  # Leave some room for safety
        """Split text into chunks that fit in Discord embed fields"""
        if len(text) <= max_length:
            return [text]
        
        chunks = []
        current_pos = 0
        
        while current_pos < len(text):
            if current_pos + max_length >= len(text):
                # Last chunk
                chunks.append(text[current_pos:])
                break
            
            # Find a good breaking point (prefer word boundaries)
            chunk_end = current_pos + max_length
            
            # Look for word boundary within last 100 characters
            best_break = chunk_end
            for i in range(chunk_end - 100, chunk_end):
                if i > current_pos and text[i] in [' ', '\n', '\t', '.', ',', '!', '?', ';']:
                    best_break = i + 1
                    break
            
            chunks.append(text[current_pos:best_break])
            current_pos = best_break
        
        return chunks
    
    # Create the main embed
    main_embed = discord.Embed(
        title=get_translation(ui_lang, "TEXTTR.title")[:256],
        color=embed_color
    )
    
    embeds_to_send = [main_embed]
    current_embed = main_embed
    field_count = 0
    
    # Add original text fields (if not hidden)
    if user_id not in hidden_sessions:
        original_chunks = split_text_for_fields(original_text)
        for i, chunk in enumerate(original_chunks):
            field_name = original_field_name if i == 0 else f"{original_field_name} (continued {i+1})"
            
            result, field_count = add_field_to_embed(current_embed, field_name, chunk, field_count)
            if result is None:
                # Need a new embed
                new_embed = discord.Embed(
                    title=f"{get_translation(ui_lang, 'TEXTTR.title')} (continued)",
                    color=embed_color
                )
                embeds_to_send.append(new_embed)
                current_embed = new_embed
                field_count = 0
                current_embed.add_field(name=field_name, value=chunk, inline=False)
                field_count += 1
    
    # Add translation fields
    translation_chunks = split_text_for_fields(translated_text)
    for i, chunk in enumerate(translation_chunks):
        field_name = translation_field_name if i == 0 else f"{translation_field_name} (continued {i+1})"
        
        result, field_count = add_field_to_embed(current_embed, field_name, chunk, field_count)
        if result is None:
            # Need a new embed
            new_embed = discord.Embed(
                title=f"{get_translation(ui_lang, 'TEXTTR.title')} (continued)",
                color=embed_color
            )
            embeds_to_send.append(new_embed)
            current_embed = new_embed
            field_count = 0
            current_embed.add_field(name=field_name, value=chunk, inline=False)
            field_count += 1
    
    # Add points field to the last embed
    result, field_count = add_field_to_embed(current_embed, points_field_name, points_field_value, field_count)
    if result is None:
        # Need a new embed for points field
        new_embed = discord.Embed(
            title=f"{get_translation(ui_lang, 'TEXTTR.title')} (continued)",
            color=embed_color
        )
        embeds_to_send.append(new_embed)
        current_embed = new_embed
        current_embed.add_field(name=points_field_name, value=points_field_value, inline=True)
    
    # Set footer on the last embed
    embeds_to_send[-1].set_footer(text=footer_text)
    
    # Send all embeds
    await interaction.followup.send(embed=embeds_to_send[0], ephemeral=False)
    
    # Send additional embeds as followups if needed
    for additional_embed in embeds_to_send[1:]:
        await interaction.followup.send(embed=additional_embed, ephemeral=False)


@text_translate.autocomplete('source_lang')
async def source_lang_autocomplete(interaction: discord.Interaction, current: str):
    return await translated_language_autocomplete(interaction, current)

@text_translate.autocomplete('target_lang')
async def target_lang_autocomplete(interaction: discord.Interaction, current: str):
    return await translated_language_autocomplete(interaction, current)

async def translated_language_autocomplete(
    interaction: discord.Interaction,
    current: str,
) -> list[app_commands.Choice[str]]:
    user_id = interaction.user.id
    ui_lang = await get_user_ui_language(user_id)
    current_lower = current.lower()
    matches = []

    for code, name in languages.items():
        translated_name = get_translation(ui_lang, f"LANGUAGES.{code}", default=name)
        if current_lower in translated_name.lower() or current_lower in code.lower():
            matches.append(app_commands.Choice(
                name=f"{translated_name} ({code})",  # what the user sees
                value=code                           # what the command receives
            ))

    return matches[:25]

# Add autocomplete to the texttr command
text_translate.autocomplete('source_lang')(translated_language_autocomplete)
text_translate.autocomplete('target_lang')(translated_language_autocomplete)


@tree.command(name="voice", description="Translate text and convert to speech")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(
    text="Text to translate and convert to speech",
    source_lang="Source language (type to search)",
    target_lang="Target language (type to search)")
async def translate_and_speak(
    interaction: discord.Interaction,
    text: str,
    source_lang: str,
    target_lang: str):
    try:
        user_id = interaction.user.id
        
        # Get user's UI language
        ui_lang = await get_user_ui_language(user_id)
               
        # Create/update user in database
        await db.get_or_create_user(user_id, interaction.user.display_name)
               
        # Check user tier and get limits
        if user_id in tier_handler.pro_users:
            tier = 'pro'
            is_premium = True
        elif user_id in tier_handler.premium_users:
            tier = 'premium'
            is_premium = True
        elif user_id in tier_handler.basic_users:
            tier = 'basic'
            is_premium = False
        else:
            tier = 'free'
            is_premium = False
               
        limits = tier_handler.get_limits(user_id)
        
        # Convert language inputs to codes
        source_code = "auto" if source_lang.lower() == "auto" else get_language_code(source_lang)
        target_code = get_language_code(target_lang)
        if target_code == "auto":
            await interaction.response.send_message(
                get_translation(ui_lang, "AUTO.error_auto_not_allowed_for_target"),
                ephemeral=True
            )
            return
        
        if interaction.guild:
            allowed = await db.is_translation_allowed(
                interaction.guild.id,
                interaction.channel.id,
                "text" or "voice",  # depends on the command
                target_code         # or the relevant language code
            )
            if not allowed:
                await interaction.response.send_message(
                    get_translation(ui_lang, "VOICE.error_language_not_allowed"),
                    ephemeral=True
                )
                return
        
        # Validate language codes
        if not source_code:
            await interaction.response.send_message(
                get_translation(ui_lang, "VOICE.error_invalid_source", language=source_lang),
                ephemeral=True
            )
            return
                   
        if not target_code:
            await interaction.response.send_message(
                get_translation(ui_lang, "VOICE.error_invalid_target", language=target_lang),
                ephemeral=True
            )
            return
        
        # Check text length against limits
        if len(text) > limits['text_limit']:
            await interaction.response.send_message(
                get_translation(ui_lang, "VOICE.error_text_too_long", 
                              tier=tier, limit=limits['text_limit']),
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
        
        # Award points based on tier (SYNC - no await)
        points_map = {'free': 1, 'basic': 2, 'premium': 3, 'pro': 4}
        points_awarded = points_map[tier]
        reward_db.add_points(user_id, points_awarded, f"Voice translation: {source_code}→{target_code}")
               
        # Track usage and save translation (ASYNC)
        await db.track_usage(user_id, text_chars=len(text))
        await db.save_translation(
            user_id=user_id,
            guild_id=interaction.guild_id or 0,
            original_text=text,
            translated_text=translated_text,
            source_lang=source_code,
            target_lang=target_code,
            translation_type="voice"
        )
               
        # Track for achievements (SYNC - no await)
        achievement_db.track_translation(user_id, source_code, target_code, is_premium)
        new_achievements = achievement_db.check_achievements(user_id)
        if new_achievements:
            await send_achievement_notification(client, user_id, new_achievements)
        
        username = interaction.user.display_name
        
        # After checking/awarding achievements:
        uncashed_points, _ = reward_db.get_uncashed_achievement_points(user_id)
        await notify_uncashed_achievements(user_id, username, uncashed_points)
        
        # Create temporary file using BytesIO instead of a file
        mp3_fp = io.BytesIO()
        tts = gTTS(text=translated_text, lang=target_code)
        tts.write_to_fp(mp3_fp)
        mp3_fp.seek(0)
        
        # Create and send the voice translation embeds
        await create_and_send_voice_embeds(
            interaction=interaction,
            original_text=text,
            translated_text=translated_text,
            source_code=source_code,
            target_code=target_code,
            tier=tier,
            points_awarded=points_awarded,
            limits=limits,
            ui_lang=ui_lang,
            user_id=user_id
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
        # Get UI language for error message
        try:
            ui_lang = await get_user_ui_language(interaction.user.id)
        except:
            ui_lang = 'en'  # Fallback
            
        if not interaction.response.is_done():
            await interaction.response.send_message(
                get_translation(ui_lang, "VOICE.error_general", error=str(e)),
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                get_translation(ui_lang, "VOICE.error_general", error=str(e)),
                ephemeral=True
            )


async def create_and_send_voice_embeds(
    interaction: discord.Interaction,
    original_text: str,
    translated_text: str,
    source_code: str,
    target_code: str,
    tier: str,
    points_awarded: int,
    limits: dict,
    ui_lang: str,
    user_id: int
):
    """Create and send voice translation embeds with proper truncation and splitting"""
    
    # Get language names and flags
    source_name = get_translation(ui_lang, f"LANGUAGES.{source_code}", default=languages.get(source_code, source_code))
    target_name = get_translation(ui_lang, f"LANGUAGES.{target_code}", default=languages.get(target_code, target_code))
    source_flag = flag_mapping.get(source_code, '🌐')
    target_flag = flag_mapping.get(target_code, '🌐')
    
    # Tier colors
    tier_colors = {'free': 0x95a5a6, 'basic': 0x3498db, 'premium': 0xf39c12, 'pro': 0x9b59b6}
    embed_color = tier_colors.get(tier, discord.Color.greyple())
    
    # Calculate footer text
    if tier == 'free':
        footer_text = get_translation(ui_lang, "VOICE.footer_free")
    elif tier == 'basic':
        footer_text = get_translation(ui_lang, "VOICE.footer_basic")
    elif tier == 'premium':
        footer_text = get_translation(ui_lang, "VOICE.footer_premium")
    else:  # pro
        footer_text = get_translation(ui_lang, "VOICE.footer_pro")

    # Add context info
    if interaction.guild:
        footer_text += " " + get_translation(ui_lang, "VOICE.footer_server", 
                                            server=interaction.guild.name)
    else:
        footer_text += " " + get_translation(ui_lang, "VOICE.footer_dm")
    
    footer_text = footer_text[:2048]  # Discord footer limit
    
    # Field names (truncated to Discord's 256 character limit)
    original_field_name = get_translation(ui_lang, "VOICE.original_field", flag=source_flag, language=source_name)[:256]
    translation_field_name = get_translation(ui_lang, "VOICE.translation_field", flag=target_flag, language=target_name)[:256]
    points_field_name = get_translation(ui_lang, "VOICE.points_field")[:256]
    points_field_value = get_translation(ui_lang, "VOICE.points_value", points=points_awarded)[:1024]
    
    # Helper function to add field and handle embed limits
    def add_field_to_embed(embed_obj, field_name, field_value, field_counter):
        """Helper function to add field and handle embed limits"""
        # Check if current embed can hold another field (Discord limit is 25 fields per embed)
        if field_counter >= 25:
            return None, field_counter  # Signal that we need a new embed
        
        embed_obj.add_field(
            name=field_name,
            value=field_value,
            inline=False
        )
        return embed_obj, field_counter + 1
    
    # Split texts into chunks that fit Discord's 1024 character field limit
    def split_text_for_fields(text, max_length=1020):  # Leave some room for safety
        """Split text into chunks that fit in Discord embed fields"""
        if len(text) <= max_length:
            return [text]
        
        chunks = []
        current_pos = 0
        
        while current_pos < len(text):
            if current_pos + max_length >= len(text):
                # Last chunk
                chunks.append(text[current_pos:])
                break
            
            # Find a good breaking point (prefer word boundaries)
            chunk_end = current_pos + max_length
            
            # Look for word boundary within last 100 characters
            best_break = chunk_end
            for i in range(chunk_end - 100, chunk_end):
                if i > current_pos and text[i] in [' ', '\n', '\t', '.', ',', '!', '?', ';']:
                    best_break = i + 1
                    break
            
            chunks.append(text[current_pos:best_break])
            current_pos = best_break
        
        return chunks
    
    # Create the main embed
    main_embed = discord.Embed(
        title=get_translation(ui_lang, "VOICE.title")[:256],
        color=embed_color
    )
    
    embeds_to_send = [main_embed]
    current_embed = main_embed
    field_count = 0
    
    # Add original text fields (if not hidden)
    if user_id not in hidden_sessions:
        original_chunks = split_text_for_fields(original_text)
        for i, chunk in enumerate(original_chunks):
            field_name = original_field_name if i == 0 else f"{original_field_name} (continued {i+1})"
            
            result, field_count = add_field_to_embed(current_embed, field_name, chunk, field_count)
            if result is None:
                # Need a new embed
                new_embed = discord.Embed(
                    title=f"{get_translation(ui_lang, 'VOICE.title')} (continued)",
                    color=embed_color
                )
                embeds_to_send.append(new_embed)
                current_embed = new_embed
                field_count = 0
                current_embed.add_field(name=field_name, value=chunk, inline=False)
                field_count += 1
    
    # Add translation fields
    translation_chunks = split_text_for_fields(translated_text)
    for i, chunk in enumerate(translation_chunks):
        field_name = translation_field_name if i == 0 else f"{translation_field_name} (continued {i+1})"
        
        result, field_count = add_field_to_embed(current_embed, field_name, chunk, field_count)
        if result is None:
            # Need a new embed
            new_embed = discord.Embed(
                title=f"{get_translation(ui_lang, 'VOICE.title')} (continued)",
                color=embed_color
            )
            embeds_to_send.append(new_embed)
            current_embed = new_embed
            field_count = 0
            current_embed.add_field(name=field_name, value=chunk, inline=False)
            field_count += 1
    
    # Add points field to the last embed
    result, field_count = add_field_to_embed(current_embed, points_field_name, points_field_value, field_count)
    if result is None:
        # Need a new embed for points field
        new_embed = discord.Embed(
            title=f"{get_translation(ui_lang, 'VOICE.title')} (continued)",
            color=embed_color
        )
        embeds_to_send.append(new_embed)
        current_embed = new_embed
        current_embed.add_field(name=points_field_name, value=points_field_value, inline=True)
    
    # Set footer on the last embed
    embeds_to_send[-1].set_footer(text=footer_text)
    
    # Send all embeds
    await interaction.followup.send(embed=embeds_to_send[0], ephemeral=True)
    
    # Send additional embeds as followups if needed
    for additional_embed in embeds_to_send[1:]:
        await interaction.followup.send(embed=additional_embed, ephemeral=True)


# Add autocomplete to voice command
translate_and_speak.autocomplete('source_lang')(translated_language_autocomplete)
translate_and_speak.autocomplete('target_lang')(translated_language_autocomplete)
# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger('muse')

# Voice state event handlers for auto-disconnect
@client.event
async def on_voice_state_update(member, before, after):
    """Handle voice state changes - auto disconnect when channel is empty"""
    try:
        # Only process if bot is connected to voice
        if not member.guild.voice_client:
            return
            
        # If the bot was moved or disconnected
        if member.id == client.user.id:
            if before.channel and not after.channel:
                # Bot was disconnected, clean up session
                guild_id = member.guild.id
                if guild_id in voice_translation_sessions:
                    del voice_translation_sessions[guild_id]
                    logger.info(f"Cleaned up voice session for guild {guild_id} - bot disconnected")
            return
            
        # Check if anyone left the bot's voice channel
        bot_channel = member.guild.voice_client.channel
        if before.channel == bot_channel:
            # Count remaining humans in the channel (exclude bots)
            humans_in_channel = len([m for m in bot_channel.members if not m.bot])
            
            if humans_in_channel == 0:
                # No humans left, disconnect after a short delay
                logger.info(f"No humans left in {bot_channel.name}, disconnecting in 10 seconds")
                await asyncio.sleep(10)
                
                # Check again in case someone rejoined
                humans_in_channel = len([m for m in bot_channel.members if not m.bot])
                if humans_in_channel == 0 and member.guild.voice_client:
                    try:
                        # Clean up session and calculate duration
                        guild_id = member.guild.id
                        session_duration_seconds = 0
                        text_channel = None
                        initiating_user_id = None
                        
                        if guild_id in voice_translation_sessions:
                            session = voice_translation_sessions[guild_id]
                            
                            # Calculate session duration
                            if 'start_time' in session:
                                session_duration_seconds = time.time() - session['start_time']
                            
                            # Get text channel and user info for notification
                            text_channel = session.get('text_channel')
                            initiating_user_id = session.get('initiating_user_id')
                            
                            # Send session stats BEFORE cleanup and deletion
                            if text_channel and session_duration_seconds > 0:
                                try:
                                    # Check if it's a voicechat2 session
                                    session_type = session.get('type')
                                    logger.info(f"Auto-disconnect - Session type: {session_type}")
                                    if session_type in ['voicechat2', 'enhanced_v2']:
                                        # Use the dedicated voicechat2 stats function
                                        logger.info("Sending voicechat2 auto-disconnect stats")
                                        await send_voicechat2_session_stats(guild_id, "auto_disconnect")
                                    else:
                                        # Regular voicechat session
                                        duration_str = format_seconds(int(session_duration_seconds))
                                        embed = discord.Embed(
                                            title="🔄 Voice Translation Auto-Disconnected",
                                            description=f"Bot automatically disconnected from **{bot_channel.name}** due to empty voice channel.",
                                            color=0xffa500
                                        )
                                        embed.add_field(
                                            name="📊 Session Stats",
                                            value=f"🎤 Voice session duration: {duration_str}",
                                            inline=False
                                        )
                                        embed.set_footer(text="You can start a new session with /voicechat")
                                        
                                        await text_channel.send(embed=embed)
                                except Exception as embed_error:
                                    logger.error(f"Error sending auto-disconnect notification: {embed_error}")
                            
                            # Now cleanup and delete session
                            if 'sink' in session:
                                sink = session['sink']
                                if hasattr(sink, 'cleanup'):
                                    if asyncio.iscoroutinefunction(sink.cleanup):
                                        await sink.cleanup()
                                    else:
                                        sink.cleanup()
                            del voice_translation_sessions[guild_id]
                        
                        await member.guild.voice_client.disconnect()
                        logger.info(f"Auto-disconnected from empty voice channel: {bot_channel.name}")
                        
                    except Exception as e:
                        logger.error(f"Error auto-disconnecting: {e}")
                        
    except Exception as e:
        logger.error(f"Error in voice state update: {e}")

# Update the voice chat commands to use new limits (complete voicechat command)
@tree.command(name="voicechat", description="Translate voice chat in real-time")
@app_commands.describe(
    source_lang="Source language (type to search, or 'auto' for detection)",
    target_lang="Target language (type to search)")
async def voice_chat_translate(
    interaction: discord.Interaction,
    source_lang: str,
    target_lang: str):
    
    await track_command_usage(interaction)
    
    user_id = interaction.user.id
    
    # Get user's UI language
    ui_lang = await get_user_ui_language(user_id)
    
    # Check if command is used in a guild
    if not interaction.guild:
        embed = discord.Embed(
            title=get_translation(ui_lang, "VOICECHAT.error_server_only"),
            description=get_translation(ui_lang, "VOICECHAT.error_server_only_desc"),
            color=0xFF0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
           
    # Check if user is in a voice channel
    if not interaction.user.voice:
        await interaction.response.send_message(
            get_translation(ui_lang, "VOICECHAT.error_not_in_voice"),
            ephemeral=True
        )
        return
           
    # Convert language inputs to codes - support both codes and names
    source_code = "auto" if source_lang.lower() == "auto" else get_language_code(source_lang)
    target_code = get_language_code(target_lang)
    if target_code == "auto":
            await interaction.response.send_message(
                get_translation(ui_lang, "AUTO.error_auto_not_allowed_for_target"),
                ephemeral=True
            )
            return
    
    if interaction.guild:
        allowed = await db.is_translation_allowed(
            interaction.guild.id,
            interaction.channel.id,
            "text" or "voice",  # depends on the command
            target_code         # or the relevant language code
        )
        if not allowed:
            await interaction.response.send_message(
                get_translation(ui_lang, "VOICECHAT.error_language_not_allowed"),
                ephemeral=True
            )
            return
    
        # Validate language codes
    if source_lang.lower() != "auto" and not source_code:
        await interaction.response.send_message(
            get_translation(ui_lang, "VOICECHAT.error_invalid_source", language=source_lang),
            ephemeral=True
        )
        return
           
    if not target_code:
        await interaction.response.send_message(
            get_translation(ui_lang, "VOICECHAT.error_invalid_target", language=target_lang),
            ephemeral=True
        )
        return
           
    # Get user's tier and check voice limits
    user = await db.get_or_create_user(user_id, interaction.user.display_name)
    current_tier = tier_handler.get_user_tier(user_id)
    
    # Check voice limits using tier handler
    can_use_voice, limit_message = tier_handler.check_usage_limits(
        user_id,
        usage_type='voice_seconds',
        amount=1  # Just checking if they can start a session
    )
    
    if not can_use_voice:
        # Get tier-specific upgrade messages
        tier_upgrade_key = f"VOICECHAT.tier_upgrade_{current_tier}"
        
        embed = discord.Embed(
            title=get_translation(ui_lang, "VOICECHAT.error_daily_limit_title"),
            description=get_translation(ui_lang, tier_upgrade_key),
            color=0xFF6B6B
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Check if user is close to their limit (warn them)
    if current_tier != 'pro':  # Pro has unlimited
        usage_stats = tier_handler.get_usage_stats(user_id)
        remaining_limits = tier_handler.get_remaining_limits(user_id)
           
        if remaining_limits['voice_seconds'] < 300:  # Less than 5 minutes remaining
            embed = discord.Embed(
                title=get_translation(ui_lang, "VOICECHAT.warning_limit_title"),
                description=get_translation(ui_lang, "VOICECHAT.warning_limit_desc", 
                                          remaining=format_seconds(remaining_limits['voice_seconds'])),
                color=0xF39C12
            )
            # Don't return here, just warn them
       
    voice_channel = interaction.user.voice.channel
    user = await db.get_or_create_user(user_id, interaction.user.display_name)
    limits = get_effective_limits(user_id, tier_handler, reward_db)
    
    # --- TIER PRIORITY LOGIC START ---
    guild_id = interaction.guild_id
    current_tier = tier_handler.get_user_tier(user_id)
    tier_order = ['free', 'basic', 'premium', 'pro']
    
    # If a session is already running in this guild
    if guild_id in voice_translation_sessions:
        session = voice_translation_sessions[guild_id]
        owner_id = session.get('initiating_user_id')
        if owner_id and owner_id != user_id:
            owner_tier = tier_handler.get_user_tier(owner_id)
            # Only allow takeover if the new user's tier is higher
            if tier_order.index(current_tier) <= tier_order.index(owner_tier):
                embed = discord.Embed(
                    title=get_translation(ui_lang, "VOICECHAT.error_session_in_use_title"),
                    description=get_translation(ui_lang, "VOICECHAT.error_session_in_use_desc",
                                              tier=owner_tier.title(), owner_id=owner_id),
                    color=0xFF6B6B
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            else:
                # Stop the current session before starting a new one
                try:
                    if session['voice_client'].is_listening():
                        session['voice_client'].stop_listening()
                    if 'sink' in session:
                        await session['sink'].cleanup()
                    if session['voice_client'].is_playing():
                        session['voice_client'].stop()
                    await session['voice_client'].disconnect()
                except Exception as e:
                    logger.error(f"Error stopping previous session: {e}")
                del voice_translation_sessions[guild_id]
    
    # Define the TranslationSink class with usage tracking
    class TranslationSink(BasicSink):
        def __init__(self, *, source_language, target_language, text_channel, client_instance, user_id, ui_language):
            # Must call super().__init__() as per documentation
            self.event = asyncio.Event()
            super().__init__(self.event)
            self.source_language = source_language
            self.target_language = target_language
            self.text_channel = text_channel
            self.client_instance = client_instance
            self.initiating_user_id = user_id
            self.ui_language = ui_language
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
                           
                # Create/update user in database
                await db.get_or_create_user(user_id, username)
                           
                # Check user tier
                if user_id in tier_handler.pro_users:
                    tier = 'pro'
                    is_premium = True
                elif user_id in tier_handler.premium_users:
                    tier = 'premium'
                    is_premium = True
                elif user_id in tier_handler.basic_users:
                    tier = 'basic'
                    is_premium = False
                else:
                    tier = 'free'
                    is_premium = False
                           
                # Award points based on tier (SYNC - no await)
                points_map = {'free': 1, 'basic': 2, 'premium': 3, 'pro': 4}
                points_awarded = points_map[tier]
                reward_db.add_points(user_id, points_awarded, f"Voice chat: {detected_lang or self.source_language}→{self.target_language}")
                           
                # Track usage and save translation (ASYNC)
                await db.track_usage(user_id, text_chars=len(original_text))
                await db.save_translation(
                    user_id=user_id,
                    guild_id=guild.id,
                    original_text=original_text,
                    translated_text=translated_text,
                    source_lang=detected_lang or self.source_language,
                    target_lang=self.target_language,
                    translation_type="voice_chat"
                )
                           
                # Track for achievements (SYNC - no await)
                achievement_db.track_translation(user_id, detected_lang or self.source_language, self.target_language, is_premium)
                new_achievements = achievement_db.check_achievements(user_id)
                if new_achievements:
                    await send_achievement_notification(client, user_id, new_achievements)
                await safe_track_voice_achievement(
                    user_id=user_id,
                    username=username
                )
                           
                # Get source language - either detected or specified
                source_lang = detected_lang if detected_lang else self.source_language
                source_name = get_translation(ui_lang, f"LANGUAGES.{source_code}", default=languages.get(source_code, source_code))
                target_name = get_translation(ui_lang, f"LANGUAGES.{target_code}", default=languages.get(target_code, target_code))
                           
                source_flag = flag_mapping.get(source_lang, '🌐')
                target_flag = flag_mapping.get(self.target_language, '🌐')
                           
                # Create embed with tier-based colors
                tier_colors = {'free': 0x95a5a6, 'basic': 0x3498db, 'premium': 0xf39c12, 'pro': 0x9b59b6}
                embed = discord.Embed(
                    title=get_translation(self.ui_language, "VOICECHAT.title", username=username),
                    color=tier_colors[tier]
                )
                           
                if user_id not in hidden_sessions:
                    embed.add_field(
                        name=get_translation(self.ui_language, "VOICECHAT.original_field", 
                                           flag=source_flag, language=source_name),
                        value=original_text,
                        inline=False
                    )
                           
                embed.add_field(
                    name=get_translation(self.ui_language, "VOICECHAT.translation_field", 
                                       flag=target_flag, language=target_name),
                    value=translated_text,
                    inline=False
                )
                           
                # Add points earned indicator
                embed.add_field(
                    name=get_translation(self.ui_language, "VOICECHAT.points_field"),
                    value=get_translation(self.ui_language, "VOICECHAT.points_value", points=points_awarded),
                    inline=True
                )
                           
                # Add tier-specific footer
                footer_key = f"VOICECHAT.footer_{tier}"
                embed.set_footer(text=get_translation(self.ui_language, footer_key))
                           
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
               
        async def cleanup(self):
            logger.info("Cleaning up TranslationSink")
            self.is_running = False
                       
            try:
                # Calculate session duration and track usage
                session_duration = int(time.time() - self.start_time)
                await db.track_usage(self.initiating_user_id, voice_seconds=session_duration)
                logger.info(f"Voice session duration: {session_duration} seconds")
            except Exception as e:
                logger.error(f"Error tracking usage during cleanup: {e}")
                       
            # Clean up processing thread
            try:
                if hasattr(self, 'processing_thread') and self.processing_thread.is_alive():
                    self.processing_thread.join(timeout=3.0)
                    if self.processing_thread.is_alive():
                        logger.warning("Processing thread didn't shut down cleanly")
            except Exception as e:
                logger.error(f"Error cleaning up processing thread: {e}")
                       
            # Clear buffers
            try:
                self.user_buffers.clear()
                while not self.processing_queue.empty():
                    try:
                        self.processing_queue.get_nowait()
                    except:
                        break
            except Exception as e:
                logger.error(f"Error clearing buffers: {e}")
                       
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
               
        # Clean up any existing connection first
        if interaction.guild.voice_client:
            logger.info("Disconnecting existing voice client")
            try:
                if interaction.guild.voice_client.is_listening():
                    interaction.guild.voice_client.stop_listening()
                await interaction.guild.voice_client.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting existing client: {e}")
                       
        # Wait a moment for cleanup
        await asyncio.sleep(1)
               
        # Clean up any existing session
        guild_id = interaction.guild_id
        if guild_id in voice_translation_sessions:
            logger.info("Cleaning up existing voice session")
            session = voice_translation_sessions[guild_id]
            try:
                if 'sink' in session:
                    await session['sink'].cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up sink: {e}")
            del voice_translation_sessions[guild_id]
               
        # Connect to voice channel with proper error handling
        logger.info(f"Connecting to voice channel with VoiceRecvClient: {voice_channel.name}")
        try:
            voice_client = await voice_channel.connect(
                cls=voice_recv.VoiceRecvClient,
                self_deaf=False,
                self_mute=False,
                timeout=30.0  # 30 second timeout
            )
            logger.info("Successfully connected to voice channel")
        except asyncio.TimeoutError:
            await interaction.followup.send(
                get_translation(ui_lang, "VOICECHAT.error_connection_timeout"), 
                ephemeral=True
            )
            return
        except Exception as e:
            logger.error(f"Failed to connect to voice channel: {e}")
            await interaction.followup.send(
                get_translation(ui_lang, "VOICECHAT.error_connection_failed", error=str(e)), 
                ephemeral=True
            )
            return
               
        # After connecting to the voice channel and assigning voice_client
        # 1. Create the sink instance
        sink = TranslationSink(
            source_language=source_code,
            target_language=target_code,
            text_channel=interaction.channel,
            client_instance=client,
            user_id=interaction.user.id,
            ui_language=ui_lang
        )
        
        # 2. Start listening with the sink
        voice_client.listen(sink)
        
        # 3. Track the session with better info
        voice_translation_sessions[interaction.guild_id] = {
            'voice_client': voice_client,
            'sink': sink,
            'channel': voice_channel,
            'type': 'voicechat',
            'languages': [source_code, target_code],
            'initiating_user_id': interaction.user.id,
            'start_time': time.time(),
            'text_channel': interaction.channel
        }
               
        # 4. Send success message with enhanced embed
        source_name = get_translation(ui_lang, f"LANGUAGES.{source_code}", default=languages.get(source_code, source_code))
        target_name = get_translation(ui_lang, f"LANGUAGES.{target_code}", default=languages.get(target_code, target_code))

        
        # Get user tier and limits info
        current_tier = tier_handler.get_user_tier(user_id)
        tier_colors = {'free': 0x95a5a6, 'basic': 0x3498db, 'premium': 0xf39c12, 'pro': 0x9b59b6}
        tier_emojis = {'free': '🆓', 'basic': '🥉', 'premium': '🥈', 'pro': '🥇'}
        
        # Get flags for languages
        source_flag = flag_mapping.get(source_code, '🌐')
        target_flag = flag_mapping.get(target_code, '🌐')
        
        # Calculate remaining voice time display using tier handler
        remaining_limits = tier_handler.get_remaining_limits(user_id)
        tier_info = tier_handler.get_tier_info(current_tier)
        
        if current_tier == 'pro':
            remaining_time_text = get_translation(ui_lang, "VOICECHAT.remaining_unlimited")
        else:
            daily_usage = await db.get_daily_usage(user_id)
            # Define limits per tier
            voice_limits = {
                'free': 1800,    # 30 minutes
                'basic': 3600,   # 1 hour  
                'premium': 7200, # 2 hours
            }
               
            limit_seconds = voice_limits.get(current_tier, 1800)
            remaining_seconds = limit_seconds - daily_usage['voice_seconds']
               
            # Format the limit display
            limit_display = {
                'free': '30 minutes',
                'basic': '1 hour',
                'premium': '2 hours'
            }
            # Ensure remaining_seconds is not negative
            remaining_seconds = max(0, remaining_seconds)
               
            remaining_time_text = get_translation(ui_lang, "VOICECHAT.remaining_limited", 
                                                remaining=format_seconds(remaining_seconds), 
                                                limit=limit_display[current_tier])
           
        embed = discord.Embed(
            title=get_translation(ui_lang, "VOICECHAT.active_title", tier_emoji=tier_emojis[current_tier]),
            description=get_translation(ui_lang, "VOICECHAT.active_desc"),
            color=tier_colors[current_tier]
        )
        
        # Language translation flow with flags
        embed.add_field(
            name=get_translation(ui_lang, "VOICECHAT.translation_flow"),
            value=get_translation(ui_lang, "VOICECHAT.translation_flow_value", 
                                source_flag=source_flag, source_name=source_name,
                                target_flag=target_flag, target_name=target_name),
            inline=False
        )
        
        # Channel information
        embed.add_field(
            name=get_translation(ui_lang, "VOICECHAT.channels"),
            value=get_translation(ui_lang, "VOICECHAT.channels_value", 
                                voice_channel=voice_channel.name, 
                                text_channel=interaction.channel.mention),
            inline=True
        )
        
        # Tier and limits information
        embed.add_field(
            name=get_translation(ui_lang, "VOICECHAT.your_tier", tier_emoji=tier_emojis[current_tier]),
            value=get_translation(ui_lang, "VOICECHAT.tier_info", 
                                tier=current_tier.title(), 
                                remaining_time=remaining_time_text),
            inline=True
        )
        
        # Points earning info
        points_map = {'free': 1, 'basic': 2, 'premium': 3, 'pro': 4}
        points_per_translation = points_map[current_tier]
        embed.add_field(
            name=get_translation(ui_lang, "VOICECHAT.points_earning"),
            value=get_translation(ui_lang, "VOICECHAT.points_earning_value", points=points_per_translation),
            inline=True
        )
        
        # Instructions section with emojis
        embed.add_field(
            name=get_translation(ui_lang, "VOICECHAT.how_to_use"),
            value=get_translation(ui_lang, "VOICECHAT.how_to_use_value"),
            inline=False
        )
        
        # Status indicators
        embed.add_field(
            name=get_translation(ui_lang, "VOICECHAT.session_status"),
            value=get_translation(ui_lang, "VOICECHAT.session_status_value", 
                                user=interaction.user.mention, 
                                timestamp=int(time.time())),
            inline=False
        )
        
        # Add tier-specific footer with upgrade hints
        footer_key = f"VOICECHAT.footer_{current_tier}_upgrade" if current_tier in ['free', 'basic'] else f"VOICECHAT.footer_{current_tier}_active"
        embed.set_footer(text=get_translation(ui_lang, footer_key))
        
        # Add a thumbnail (optional - you can use your bot's avatar or a translation icon)
        embed.set_thumbnail(url=client.user.display_avatar.url)
        
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)
               
    except Exception as e:
        logger.error(f"Error connecting to voice: {e}")
               
        # Clean up on error
        try:
            if 'voice_client' in locals() and voice_client and voice_client.is_connected():
                await voice_client.disconnect()
            if 'sink' in locals() and sink:
                await sink.cleanup()
            if interaction.guild_id in voice_translation_sessions:
                del voice_translation_sessions[interaction.guild_id]
        except Exception as cleanup_error:
            logger.error(f"Error during cleanup: {cleanup_error}")
               
        error_message = get_translation(ui_lang, "VOICECHAT.error_connection_failed", error=str(e))
        
        if not interaction.response.is_done():
            await interaction.response.send_message(error_message, ephemeral=True)
        else:
            await interaction.followup.send(error_message, ephemeral=True)




# Add autocomplete to the command (this should be OUTSIDE the function)
voice_chat_translate.autocomplete('source_lang')(translated_language_autocomplete)
voice_chat_translate.autocomplete('target_lang')(translated_language_autocomplete)

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
    await track_command_usage(interaction)
    
    user_id = interaction.user.id
    
    # Get user's UI language
    ui_lang = await get_user_ui_language(user_id)
    
    # Create/update user in database
    await db.get_or_create_user(user_id, interaction.user.display_name)
    
    # Check if command is used in a guild
    if not interaction.guild:
        embed = discord.Embed(
            title=get_translation(ui_lang, "VOICECHAT2.error_server_only"),
            description=get_translation(ui_lang, "VOICECHAT2.error_server_only_desc"),
            color=0xFF0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
        
    # Check if user is in a voice channel
    if not interaction.user.voice:
        await interaction.response.send_message(
            get_translation(ui_lang, "VOICECHAT2.error_not_in_voice"),
            ephemeral=True
        )
        return
    
    # Check user tier and get limits
    if user_id in tier_handler.pro_users:
        tier = 'pro'
        is_premium = True
    elif user_id in tier_handler.premium_users:
        tier = 'premium'
        is_premium = True
    elif user_id in tier_handler.basic_users:
        tier = 'basic'
        is_premium = False
    else:
        tier = 'free'
        is_premium = False
    
    # NEW: Check if user has access to Enhanced Voice V2
    if not has_enhanced_voice_access(user_id, reward_db, tier_handler):
        user_data = reward_db.get_or_create_user(user_id, interaction.user.display_name)
        current_tier = await tier_handler.get_user_tier_async(user_id)
        
        # Create access denied embed with purchase options
        embed = discord.Embed(
            title=get_translation(ui_lang, "VOICECHAT2.access_denied_title"),
            description=get_translation(ui_lang, "VOICECHAT2.access_denied_desc"),
            color=0x9b59b6
        )
        
        embed.add_field(
            name=get_translation(ui_lang, "VOICECHAT2.your_points"),
            value=f"{user_data['points']:,}",
            inline=True
        )
        
        embed.add_field(
            name=get_translation(ui_lang, "VOICECHAT2.beta_access_options"),
            value=get_translation(ui_lang, "VOICECHAT2.beta_access_options_desc"),
            inline=True
        )
        
        embed.add_field(
            name=get_translation(ui_lang, "VOICECHAT2.permanent_access"),
            value=get_translation(ui_lang, "VOICECHAT2.permanent_access_desc"),
            inline=True
        )
        
        embed.add_field(
            name=get_translation(ui_lang, "VOICECHAT2.features_title"),
            value=get_translation(ui_lang, "VOICECHAT2.features_desc"),
            inline=False
        )
        
        embed.add_field(
            name=get_translation(ui_lang, "VOICECHAT2.how_to_get_points"),
            value=get_translation(ui_lang, "VOICECHAT2.how_to_get_points_desc"),
            inline=False
        )
        
        embed.add_field(
            name=get_translation(ui_lang, "VOICECHAT2.current_status"),
            value=get_translation(ui_lang, "VOICECHAT2.current_status_desc", tier=current_tier.title()),
            inline=False
        )
        
        # Add purchase buttons
        view = discord.ui.View()
        
        # 1-Day Access Button
        if user_data['points'] >= 50:
            view.add_item(discord.ui.Button(
                label=get_translation(ui_lang, "VOICECHAT2.buy_1day"),
                style=discord.ButtonStyle.green,
                custom_id="buy_enhanced_voice_1day"
            ))
        else:
            view.add_item(discord.ui.Button(
                label=get_translation(ui_lang, "VOICECHAT2.buy_1day_need_points"),
                style=discord.ButtonStyle.gray,
                disabled=True
            ))
        
        # Beta Trial Button
        if user_data['points'] >= 100:
            view.add_item(discord.ui.Button(
                label=get_translation(ui_lang, "VOICECHAT2.buy_trial"),
                style=discord.ButtonStyle.blurple,
                custom_id="buy_enhanced_voice_trial"
            ))
        else:
            view.add_item(discord.ui.Button(
                label=get_translation(ui_lang, "VOICECHAT2.buy_trial_need_points"),
                style=discord.ButtonStyle.gray,
                disabled=True
            ))
        
        # 7-Day Access Button
        if user_data['points'] >= 300:
            view.add_item(discord.ui.Button(
                label=get_translation(ui_lang, "VOICECHAT2.buy_7day"),
                style=discord.ButtonStyle.red,
                custom_id="buy_enhanced_voice_7day"
            ))
        else:
            view.add_item(discord.ui.Button(
                label=get_translation(ui_lang, "VOICECHAT2.buy_7day_need_points"),
                style=discord.ButtonStyle.gray,
                disabled=True
            ))
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        return

    # Convert language inputs to codes - support both codes and names
    source_code = "auto" if language1.lower() == "auto" else get_language_code(language1)
    target_code = "auto" if language2.lower() == "auto" else get_language_code(language2)
    
    if interaction.guild:
        allowed_lang1 = await db.is_translation_allowed(
            interaction.guild.id,
            interaction.channel.id,
            "voice",
            language1 if language1 != "auto" else None
        )
        allowed_lang2 = await db.is_translation_allowed(
            interaction.guild.id,
            interaction.channel.id,
            "voice",
            language2 if language2 != "auto" else None
        )
        if not allowed_lang1 or not allowed_lang2:
            await interaction.response.send_message(
                get_translation(ui_lang, "VOICECHAT2.error_language_not_allowed"),
                ephemeral=True
            )
            return
    
    # Validate language codes (at least one must not be auto)
    if language1.lower() != "auto" and not source_code:
        await interaction.response.send_message(
            get_translation(ui_lang, "ERRORS.invalid_source", language=language1),
            ephemeral=True
        )
        return
        
    if language2.lower() != "auto" and not target_code:
        await interaction.response.send_message(
            get_translation(ui_lang, "ERRORS.invalid_target", language=language2),
            ephemeral=True
        )
        return
    
    # Don't allow both languages to be auto
    if source_code == "auto" and target_code == "auto":
        await interaction.response.send_message(
            get_translation(ui_lang, "VOICECHAT2.error_both_auto"),
            ephemeral=True
        )
        return
    
    # Get user's tier limits
    limits = tier_handler.get_limits(user_id)
    
    voice_channel = interaction.user.voice.channel
    
    # Define the Enhanced Bidirectional TranslationSink class for voicechat2
    class EnhancedBidirectionalTranslationSink(BasicSink):
        def __init__(self, *, language1, language2, text_channel, client_instance, ui_lang):
            self.event = asyncio.Event()
            super().__init__(self.event)
            self.language1 = language1  # Can be "auto"
            self.language2 = language2  # Can be "auto"
            self.text_channel = text_channel
            self.client_instance = client_instance
            self.ui_lang = ui_lang  # Store user's language preference
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
                
                # Create/update user in database
                await db.get_or_create_user(user_id, username)
                
                # Check user tier
                if user_id in tier_handler.pro_users:
                    tier = 'pro'
                    is_premium = True
                elif user_id in tier_handler.premium_users:
                    tier = 'premium'
                    is_premium = True
                elif user_id in tier_handler.basic_users:
                    tier = 'basic'
                    is_premium = False
                else:
                    tier = 'free'
                    is_premium = False
                
                guild_id = interaction.guild_id
                current_tier = tier_handler.get_user_tier(user_id)
                tier_order = ['free', 'basic', 'premium', 'pro']

                # If a session is already running in this guild
                if guild_id in voice_translation_sessions:
                    session = voice_translation_sessions[guild_id]
                    owner_id = session.get('initiating_user_id')
                    if owner_id and owner_id != user_id:
                        owner_tier = tier_handler.get_user_tier(owner_id)
                        # Only allow takeover if the new user's tier is higher
                        if tier_order.index(current_tier) <= tier_order.index(owner_tier):
                            embed = discord.Embed(
                                title=get_translation(self.ui_lang, "VOICECHAT2.error_session_in_use_title"),
                                description=get_translation(self.ui_lang, "VOICECHAT2.error_session_in_use_desc", 
                                                          tier=owner_tier.title(), owner_id=owner_id),
                                color=0xFF6B6B
                            )
                            await interaction.response.send_message(embed=embed, ephemeral=True)
                            return
                        else:
                            # Stop the current session before starting a new one
                            try:
                                if session['voice_client'].is_listening():
                                    session['voice_client'].stop_listening()
                                if 'sink' in session:
                                    session['sink'].cleanup()
                                if session['voice_client'].is_playing():
                                    session['voice_client'].stop()
                                await session['voice_client'].disconnect()
                            except Exception as e:
                                logger.error(f"Error stopping previous session: {e}")
                            del voice_translation_sessions[guild_id]
                
                # Award points based on tier (SYNC - no await)
                points_map = {'free': 2, 'basic': 3, 'premium': 4, 'pro': 5}  # Higher points for enhanced voice chat
                points_awarded = points_map[tier]
                reward_db.add_points(user_id, points_awarded, f"Enhanced voice chat: {detected_lang}→{target_lang}")
                
                # Track usage and save translation (ASYNC)
                await db.track_usage(user_id, text_chars=len(original_text))
                await db.save_translation(
                    user_id=user_id,
                    guild_id=guild.id,
                    original_text=original_text,
                    translated_text=translated_text,
                    source_lang=detected_lang,
                    target_lang=target_lang,
                    translation_type="voice_chat_v2"
                )
                
                # Track for achievements (SYNC - no await)
                achievement_db.track_translation(user_id, detected_lang, target_lang, is_premium)
                new_achievements = achievement_db.check_achievements(user_id)
                if new_achievements:
                    await send_achievement_notification(client, user_id, new_achievements)
                
                # Get language names and flags
                source_name = get_translation(ui_lang, f"LANGUAGES.{source_code}", default=languages.get(source_code, source_code))
                target_name = get_translation(ui_lang, f"LANGUAGES.{target_code}", default=languages.get(target_code, target_code))
                source_flag = flag_mapping.get(detected_lang, '🌐')
                target_flag = flag_mapping.get(target_lang, '🌐')
                
                # Create embed with tier-based colors
                tier_colors = {'free': 0x95a5a6, 'basic': 0x3498db, 'premium': 0xf39c12, 'pro': 0x9b59b6}
                embed = discord.Embed(
                    title=get_translation(self.ui_lang, "VOICECHAT2.translation_title", username=username),
                    color=tier_colors[tier]
                )
                
                if user_id not in hidden_sessions:
                    embed.add_field(
                        name=get_translation(self.ui_lang, "VOICECHAT2.detected_field", 
                                           source_flag=source_flag, source_name=source_name),
                        value=original_text[:1024],
                        inline=False
                    )
                
                embed.add_field(
                    name=get_translation(self.ui_lang, "VOICECHAT2.translation_field",
                                       target_flag=target_flag, target_name=target_name),
                    value=translated_text[:1024],
                    inline=False
                )
                
                # Add points earned indicator
                embed.add_field(
                    name=get_translation(self.ui_lang, "VOICECHAT2.points_field"),
                    value=f"+{points_awarded}",
                    inline=True
                )
                
                # Add language pair info in footer with tier
                lang1_display = "Auto-detect" if self.language1 == "auto" else languages.get(self.language1, self.language1)
                lang2_display = "Auto-detect" if self.language2 == "auto" else languages.get(self.language2, self.language2)
                
                tier_indicators = {'free': '🆓', 'basic': '🥉', 'premium': '🥈', 'pro': '🥇'}
                embed.set_footer(text=get_translation(self.ui_lang, "VOICECHAT2.footer_enhanced",
                                                    tier_indicator=tier_indicators[tier],
                                                    lang1_display=lang1_display,
                                                    lang2_display=lang2_display))
                
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
    
        # Get user's current tier and calculate limits BEFORE connecting
        current_tier = tier_handler.get_user_tier(user_id)
        daily_usage = await db.get_daily_usage(user_id)
    
        # Check voice limits before starting session
        voice_limits = {
            'free': 1800,    # 30 minutes
            'basic': 3600,   # 1 hour  
            'premium': 7200, # 2 hours
            'pro': float('inf')  # Unlimited
        }
    
        limit_seconds = voice_limits.get(current_tier, 1800)
        if current_tier != 'pro' and daily_usage['voice_seconds'] >= limit_seconds:
            remaining_seconds = 0
            embed = discord.Embed(
                title=get_translation(ui_lang, "VOICECHAT.error_daily_limit_title"),
                description=get_translation(ui_lang, "VOICECHAT.error_daily_limit_desc"),
                color=0xFF6B6B
            )
            embed.add_field(
                name=get_translation(ui_lang, "VOICECHAT.daily_limit"),
                value=f"{format_seconds(limit_seconds)} per day",
                inline=True
            )
            embed.add_field(
                name=get_translation(ui_lang, "VOICECHAT.used_today"),
                value=f"{format_seconds(daily_usage['voice_seconds'])}",
                inline=True
            )
            embed.add_field(
                name=get_translation(ui_lang, "VOICECHAT.solutions"),
                value=get_translation(ui_lang, "VOICECHAT.solutions_desc"),
                inline=False
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
    
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
                get_translation(ui_lang, "VOICECHAT2.error_connection_failed", error="Connection failed"),
                ephemeral=True
            )
            return
        
        logger.info(f"Voice client connected: {voice_client.is_connected()}")
    
        # Create our enhanced sink
        logger.info("Creating EnhancedBidirectionalTranslationSink")
        sink = EnhancedBidirectionalTranslationSink(
            language1=source_code,
            language2=target_code,
            text_channel=interaction.channel,
            client_instance=client,
            ui_lang=ui_lang
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
            lang1_display = "Auto-detect" if source_code == "auto" else languages.get(source_code, source_code)
            lang2_display = "Auto-detect" if target_code == "auto" else languages.get(target_code, target_code)
            lang1_flag = '🔍' if source_code == "auto" else flag_mapping.get(source_code, '🌐')
            lang2_flag = '🔍' if target_code == "auto" else flag_mapping.get(target_code, '🌐')
        
            # Tier-based styling
            tier_colors = {'free': 0x95a5a6, 'basic': 0x3498db, 'premium': 0xf39c12, 'pro': 0x9b59b6}
            tier_emojis = {'free': '🆓', 'basic': '🥉', 'premium': '🥈', 'pro': '🥇'}
        
            # Create embed with tier-based styling
            embed = discord.Embed(
                title=get_translation(ui_lang, "VOICECHAT2.success_title"),
                description=get_translation(ui_lang, "VOICECHAT2.success_desc",
                                          lang1_flag=lang1_flag, lang1_display=lang1_display,
                                          lang2_flag=lang2_flag, lang2_display=lang2_display),
                color=tier_colors[current_tier]
            )
        
            # Translation flow section
            if source_code != "auto" and target_code != "auto":
                flow_text = f"{lang1_flag} **{lang1_display}** ↔ {lang2_flag} **{lang2_display}**"
                how_it_works = get_translation(ui_lang, "VOICECHAT2.how_it_works_bidirectional",
                                              lang1_display=lang1_display, lang2_display=lang2_display)
            elif source_code == "auto":
                flow_text = f"🔍 **Auto-detect** ➜ {lang2_flag} **{lang2_display}**"
                how_it_works = get_translation(ui_lang, "VOICECHAT2.how_it_works_auto_source",
                                              lang2_display=lang2_display)
            else:  # target_code == "auto"
                flow_text = f"🔍 **Auto-detect** ➜ {lang1_flag} **{lang1_display}**"
                how_it_works = get_translation(ui_lang, "VOICECHAT2.how_it_works_auto_target",
                                              lang1_display=lang1_display)
        
            embed.add_field(
                name=get_translation(ui_lang, "VOICECHAT.translation_flow"),
                value=flow_text,
                inline=False
            )
        
            # Channels info
            embed.add_field(
                name=get_translation(ui_lang, "VOICECHAT.channels"),
                value=get_translation(ui_lang, "VOICECHAT.channels_value",
                                    voice_channel=voice_channel.mention,
                                    text_channel=interaction.channel.mention),
                inline=True
            )
        
            # Your tier with remaining limits
            if current_tier == 'pro':
                remaining_time_text = get_translation(ui_lang, "VOICECHAT.remaining_unlimited")
            else:
                remaining_seconds = max(0, limit_seconds - daily_usage['voice_seconds'])
                limit_display = {
                    'free': '30 minutes',
                    'basic': '1 hour',
                    'premium': '2 hours'
                }
                remaining_time_text = get_translation(ui_lang, "VOICECHAT.remaining_limited",
                                                    remaining=format_seconds(remaining_seconds),
                                                    limit=limit_display[current_tier])
        
            embed.add_field(
                name=get_translation(ui_lang, "VOICECHAT.your_tier", tier_emoji=tier_emojis[current_tier]),
                value=get_translation(ui_lang, "VOICECHAT.tier_info",
                                    tier=current_tier.title(),
                                    remaining_time=remaining_time_text),
                inline=True
            )
        
            # Points earning (tier-based)
            points_per_translation = {'free': 2, 'basic': 3, 'premium': 4, 'pro': 5}[current_tier]
            embed.add_field(
                name=get_translation(ui_lang, "VOICECHAT2.enhanced_rewards"),
                value=get_translation(ui_lang, "VOICECHAT2.enhanced_rewards_desc", points=points_per_translation),
                inline=True
            )
        
            # How to use section
            embed.add_field(
                name=get_translation(ui_lang, "VOICECHAT.how_to_use"),
                value=get_translation(ui_lang, "VOICECHAT.how_to_use_value"),
                inline=False
            )
        
            # Enhanced V2 features
            embed.add_field(
                name=get_translation(ui_lang, "VOICECHAT2.how_it_works"),
                value=how_it_works,
                inline=False
            )
        
            # Session status
            embed.add_field(
                name=get_translation(ui_lang, "VOICECHAT.session_status"),
                value=get_translation(ui_lang, "VOICECHAT.session_status_value",
                                    user=interaction.user.mention,
                                    timestamp=int(time.time())),
                inline=False
            )
        
            # Tier-specific footer
            tier_benefits = {
                'free': get_translation(ui_lang, "VOICECHAT.footer_free_upgrade"),
                'basic': get_translation(ui_lang, "VOICECHAT.footer_basic_upgrade"),
                'premium': get_translation(ui_lang, "VOICECHAT.footer_premium_active"),
                'pro': get_translation(ui_lang, "VOICECHAT.footer_pro_active")
            }
        
            embed.set_footer(text=f"{tier_benefits[current_tier]} • Enhanced Voice V2")
        
            await interaction.followup.send(embed=embed, ephemeral=True)
        
            # Store the voice client and sink for later cleanup
            voice_translation_sessions[interaction.guild_id] = {
                'voice_client': voice_client,
                'sink': sink,
                'channel': voice_channel,
                'type': 'enhanced_v2',
                'languages': [source_code, target_code],
                'initiating_user_id': interaction.user.id,
                'start_time': time.time(),
                'text_channel': interaction.channel,
                'tier': current_tier,  # Store tier for session management
                'points_per_translation': points_per_translation
            }
        
            # Start a task to check if users leave the voice channel
            client.loop.create_task(check_voice_channel_enhanced(voice_client, voice_channel))
        
        except Exception as e:
            logger.error(f"Error starting listening: {e}")
            await interaction.followup.send(
                get_translation(ui_lang, "VOICECHAT2.error_listening_failed", error=str(e)),
                ephemeral=True
            )
        
    except Exception as e:
        logger.error(f"Error connecting to voice: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message(
                get_translation(ui_lang, "VOICECHAT2.error_connection_failed", error=str(e)),
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                get_translation(ui_lang, "VOICECHAT2.error_connection_failed", error=str(e)),
                ephemeral=True
            )



# Add autocomplete to the command
voice_chat_translate_bidirectional_v2.autocomplete('language1')(source_language_autocomplete)
voice_chat_translate_bidirectional_v2.autocomplete('language2')(source_language_autocomplete)

# Add button interaction handler for Enhanced Voice V2 purchases
@client.event
async def on_interaction(interaction):
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data.get('custom_id')
        user_id = interaction.user.id
        
        # Get user's UI language
        ui_lang = await get_user_ui_language(user_id)
        
        if custom_id in ['buy_enhanced_voice_1day', 'buy_enhanced_voice_trial', 'buy_enhanced_voice_7day']:
            user_data = reward_db.get_or_create_user(user_id, interaction.user.display_name)
            
            # Define purchase options
            purchase_options = {
                'buy_enhanced_voice_1day': {'cost': 50, 'duration': 1, 'name_key': 'SHOP.enhanced_voice_1day'},
                'buy_enhanced_voice_trial': {'cost': 100, 'duration': 2, 'name_key': 'SHOP.enhanced_voice_trial'},
                'buy_enhanced_voice_7day': {'cost': 300, 'duration': 7, 'name_key': 'SHOP.enhanced_voice_7day'}
            }
            
            option = purchase_options[custom_id]
            
            # Check if user has enough points
            if user_data['points'] < option['cost']:
                await interaction.response.send_message(
                    get_translation(ui_lang, "SHOP.insufficient_points", 
                                  cost=option['cost'], 
                                  current=user_data['points']),
                    ephemeral=True
                )
                return
            
            # Process the purchase
            try:
                # Deduct points
                item_name = get_translation(ui_lang, option['name_key'])
                reward_db.add_points(user_id, -option['cost'], f"Purchased Enhanced Voice V2: {item_name}")
                
                # Grant access
                from datetime import datetime, timedelta
                expiry_date = datetime.now() + timedelta(days=option['duration'])
                
                # Store the access in a simple way (you might want to use a proper database)
                if not hasattr(reward_db, 'enhanced_voice_access'):
                    reward_db.enhanced_voice_access = {}
                
                reward_db.enhanced_voice_access[user_id] = {
                    'expires': expiry_date,
                    'type': custom_id
                }
                
                # Success message
                embed = discord.Embed(
                    title=get_translation(ui_lang, "SHOP.purchase_success_title"),
                    description=get_translation(ui_lang, "SHOP.purchase_success_desc", item_name=item_name),
                    color=0x2ecc71
                )
                
                embed.add_field(
                    name=get_translation(ui_lang, "SHOP.points_spent"),
                    value=get_translation(ui_lang, "SHOP.points_spent_value", points=option['cost']),
                    inline=True
                )
                
                embed.add_field(
                    name=get_translation(ui_lang, "SHOP.remaining_points"),
                    value=get_translation(ui_lang, "SHOP.remaining_points_value", points=user_data['points'] - option['cost']),
                    inline=True
                )
                
                embed.add_field(
                    name=get_translation(ui_lang, "SHOP.access_expires"),
                    value=f"{expiry_date.strftime('%Y-%m-%d %H:%M UTC')}",
                    inline=False
                )
                
                embed.add_field(
                    name=get_translation(ui_lang, "SHOP.ready_to_use_title"),
                    value=get_translation(ui_lang, "SHOP.ready_to_use_desc"),
                    inline=False
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
            except Exception as e:
                logger.error(f"Error processing Enhanced Voice V2 purchase: {e}")
                await interaction.response.send_message(
                    get_translation(ui_lang, "SHOP.purchase_error"),
                    ephemeral=True
                )


# Helper function to check Enhanced Voice V2 access
def has_enhanced_voice_access(user_id, reward_db, tier_handler):
    """Check if user has access to Enhanced Voice V2"""
    
    # Premium and Pro users always have access
    current_tier = tier_handler.get_user_tier(user_id)
    if current_tier in ['premium', 'pro']:
        return True
    
    # Check temporary access purchases
    if hasattr(reward_db, 'enhanced_voice_access') and user_id in reward_db.enhanced_voice_access:
        access_info = reward_db.enhanced_voice_access[user_id]
        from datetime import datetime
        
        if datetime.now() < access_info['expires']:
            return True
        else:
            # Access expired, remove it
            del reward_db.enhanced_voice_access[user_id]
            return False
    
    return False

# Enhanced voice channel checking function (if not already defined)
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

# Helper function to send voicechat2 session stats
async def send_voicechat2_session_stats(guild_id, reason="ended", user_id=None):
    """Send session statistics for voicechat2 sessions"""
    try:
        logger.info(f"Attempting to send voicechat2 session stats for guild {guild_id}, reason: {reason}")
        
        if guild_id not in voice_translation_sessions:
            logger.warning(f"No voice session found for guild {guild_id}")
            return
            
        session = voice_translation_sessions[guild_id]
        session_type = session.get('type')
        logger.info(f"Session type: {session_type}")
        
        # Only send stats for voicechat2 sessions
        if session_type not in ['voicechat2', 'enhanced_v2']:
            logger.info(f"Skipping stats for non-voicechat2 session type: {session_type}")
            return
            
        # Get user's UI language (use session initiator if no user_id provided)
        if not user_id:
            user_id = session.get('initiating_user_id')
        
        ui_lang = 'en'  # Default fallback
        if user_id:
            try:
                ui_lang = await get_user_ui_language(user_id)
            except:
                ui_lang = 'en'
        
        # Calculate session duration
        session_duration_seconds = 0
        if 'start_time' in session:
            session_duration_seconds = time.time() - session['start_time']
            
        # Get text channel and session info
        text_channel = session.get('text_channel')
        languages = session.get('languages', [])
        
        if text_channel and session_duration_seconds > 0:
            duration_str = format_seconds(int(session_duration_seconds))
            
            # Get language names
            lang_names = []
            for lang in languages:
                if lang == "auto":
                    lang_names.append(get_translation(ui_lang, "VOICECHAT2.auto_detect"))
                else:
                    lang_names.append(languages.get(lang, lang))
            
            # Determine title and description based on reason
            if reason == "auto_disconnect":
                title = get_translation(ui_lang, "VOICECHAT2.session_auto_disconnect_title")
                description = get_translation(ui_lang, "VOICECHAT2.session_auto_disconnect_desc")
            elif reason == "manual_stop":
                title = get_translation(ui_lang, "VOICECHAT2.session_manual_stop_title")
                description = get_translation(ui_lang, "VOICECHAT2.session_manual_stop_desc")
            elif reason == "error":
                title = get_translation(ui_lang, "VOICECHAT2.session_error_title")
                description = get_translation(ui_lang, "VOICECHAT2.session_error_desc")
            else:
                title = get_translation(ui_lang, "VOICECHAT2.session_ended_title")
                description = get_translation(ui_lang, "VOICECHAT2.session_ended_desc")
            
            embed = discord.Embed(
                title=title,
                description=description,
                color=0x9b59b6
            )
            embed.add_field(
                name=get_translation(ui_lang, "VOICECHAT2.session_stats_title"),
                value=get_translation(ui_lang, "VOICECHAT2.session_stats_value", 
                                    duration=duration_str, 
                                    languages=' ↔ '.join(lang_names)),
                inline=False
            )
            embed.set_footer(text=get_translation(ui_lang, "VOICECHAT2.session_restart_footer"))
            
            # Ensure text_channel is valid before sending
            if hasattr(text_channel, 'send'):
                await text_channel.send(embed=embed)
            else:
                logger.error(f"Invalid text_channel object: {text_channel}")
                
    except Exception as e:
        logger.error(f"Error sending voicechat2 session stats: {e}")

# Enhanced voice channel checking function
async def check_voice_channel_enhanced(voice_client, voice_channel):
    """Enhanced voice channel monitoring with better error handling"""
    if not voice_client:
        return
        
    consecutive_empty_checks = 0
    error_count = 0
    guild_id = voice_client.guild.id
    
    # Get session info for user language preference
    session = voice_translation_sessions.get(guild_id, {})
    user_id = session.get('initiating_user_id')
    
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
                    
                    # Send session stats before disconnecting
                    await send_voicechat2_session_stats(guild_id, "auto_disconnect", user_id)
                    
                    # Clean up session data
                    if guild_id in voice_translation_sessions:
                        session = voice_translation_sessions[guild_id]
                        if 'sink' in session:
                            try:
                                sink = session['sink']
                                if hasattr(sink, 'cleanup'):
                                    if asyncio.iscoroutinefunction(sink.cleanup):
                                        await sink.cleanup()
                                    else:
                                        sink.cleanup()
                            except:
                                pass
                        del voice_translation_sessions[guild_id]
                        
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
                    await send_voicechat2_session_stats(guild_id, "error", user_id)
                    if guild_id in voice_translation_sessions:
                        del voice_translation_sessions[guild_id]
                    await voice_client.disconnect()
                except:
                    pass
                break
                
            await asyncio.sleep(5)

@tree.command(name="speak", description="Translate text and play speech in voice channel")
@app_commands.describe(
    text="Text to translate and play in voice channel",
    source_lang="Source language (type to search)",
    target_lang="Target language (type to search)")
async def translate_and_speak_voice(
    interaction: discord.Interaction,
    text: str,
    source_lang: str,
    target_lang: str):
    try:
        user_id = interaction.user.id
        
        # Get user's UI language
        ui_lang = await get_user_ui_language(user_id)
        
        # Create/update user in database
        await db.get_or_create_user(user_id, interaction.user.display_name)
        
        # Check if command is used in a guild
        if not interaction.guild:
            embed = discord.Embed(
                title=get_translation(ui_lang, "SPEAK.error_server_only"),
                description=get_translation(ui_lang, "SPEAK.error_server_only_desc"),
                color=0xFF0000
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
            
        # Check if user is in a voice channel
        if not interaction.user.voice:
            await interaction.response.send_message(
                get_translation(ui_lang, "SPEAK.error_not_in_voice"),
                ephemeral=True
            )
            return
        
        # Check user tier and get limits
        if user_id in tier_handler.pro_users:
            tier = 'pro'
            is_premium = True
        elif user_id in tier_handler.premium_users:
            tier = 'premium'
            is_premium = True
        elif user_id in tier_handler.basic_users:
            tier = 'basic'
            is_premium = False
        else:
            tier = 'free'
            is_premium = False
            
        limits = tier_handler.get_limits(user_id)
        
        # --- TIER PRIORITY LOGIC START ---
        guild_id = interaction.guild_id
        current_tier = tier_handler.get_user_tier(user_id)
        tier_order = ['free', 'basic', 'premium', 'pro']
        
        # If a session is already running in this guild
        if guild_id in voice_translation_sessions:
            session = voice_translation_sessions[guild_id]
            owner_id = session.get('initiating_user_id')
            if owner_id and owner_id != user_id:
                owner_tier = tier_handler.get_user_tier(owner_id)
                # Only allow takeover if the new user's tier is higher
                if tier_order.index(current_tier) <= tier_order.index(owner_tier):
                    embed = discord.Embed(
                        title=get_translation(ui_lang, "SPEAK.error_session_in_use_title"),
                        description=get_translation(ui_lang, "SPEAK.error_session_in_use_desc",
                                                  tier=owner_tier.title(), owner_id=owner_id),
                        color=0xFF6B6B
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
                else:
                    # Stop the current session before starting a new one
                    try:
                        if session['voice_client'].is_listening():
                            session['voice_client'].stop_listening()
                        if 'sink' in session:
                            session['sink'].cleanup()
                        if session['voice_client'].is_playing():
                            session['voice_client'].stop()
                        await session['voice_client'].disconnect()
                    except Exception as e:
                        logger.error(f"Error stopping previous session: {e}")
                    del voice_translation_sessions[guild_id]
        # --- TIER PRIORITY LOGIC END ---

        # Convert language inputs to codes
        source_code = "auto" if source_lang.lower() == "auto" else get_language_code(source_lang)
        target_code = get_language_code(target_lang)
        if target_code == "auto":
            await interaction.response.send_message(
                get_translation(ui_lang, "AUTO.error_auto_not_allowed_for_target"),
                ephemeral=True
            )
            return
        
        if interaction.guild:
            allowed = await db.is_translation_allowed(
                interaction.guild.id,
                interaction.channel.id,
                "text",  # or "voice" depending on your preference
                target_code
            )
            if not allowed:
                await interaction.response.send_message(
                    get_translation(ui_lang, "SPEAK.error_language_not_allowed"),
                    ephemeral=True
                )
                return
        
        # Validate language codes
        if not source_code:
            await interaction.response.send_message(
                get_translation(ui_lang, "SPEAK.error_invalid_source", language=source_lang),
                ephemeral=True
            )
            return
            
        if not target_code:
            await interaction.response.send_message(
                get_translation(ui_lang, "SPEAK.error_invalid_target", language=target_lang),
                ephemeral=True
            )
            return
        
        # Check text length against limits
        if len(text) > limits['text_limit']:
            await interaction.response.send_message(
                get_translation(ui_lang, "SPEAK.error_text_too_long", 
                              tier=tier, limit=limits['text_limit']),
                ephemeral=True
            )
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Don't translate if source and target are the same
        if source_code == target_code:
            translated_text = text
        else:
            # Translate the text
            try:
                translator = GoogleTranslator(source=source_code, target=target_code)
                translated_text = translator.translate(text)
            except Exception as e:
                await interaction.followup.send(
                    get_translation(ui_lang, "SPEAK.error_translation_failed", error=str(e)),
                    ephemeral=True
                )
                return
        
        # Award points based on tier (SYNC - no await)
        points_map = {'free': 1, 'basic': 2, 'premium': 3, 'pro': 4}
        points_awarded = points_map[tier]
        reward_db.add_points(user_id, points_awarded, f"Speak translation: {source_code}→{target_code}")
        
        # Track usage and save translation (ASYNC)
        await db.track_usage(user_id, text_chars=len(text))
        await db.save_translation(
            user_id=user_id,
            guild_id=interaction.guild_id,
            original_text=text,
            translated_text=translated_text,
            source_lang=source_code,
            target_lang=target_code,
            translation_type="speak"
        )
        
        # Track for achievements (SYNC - no await)
        achievement_db.track_translation(user_id, source_code, target_code, is_premium)
        new_achievements = achievement_db.check_achievements(user_id)
        if new_achievements:
            await send_achievement_notification(client, user_id, new_achievements)
        
        await safe_track_voice_achievement(
            user_id=interaction.user.id,
            username=interaction.user.display_name
        )
        
        username = interaction.user.display_name
        # After checking/awarding achievements:
        uncashed_points, _ = reward_db.get_uncashed_achievement_points(user_id)
        await notify_uncashed_achievements(user_id, username, uncashed_points)
        
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
        
        # Create and send the speak translation embeds
        await create_and_send_speak_embeds(
            interaction=interaction,
            original_text=text,
            translated_text=translated_text,
            source_code=source_code,
            target_code=target_code,
            tier=tier,
            points_awarded=points_awarded,
            limits=limits,
            ui_lang=ui_lang,
            user_id=user_id
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
                        get_translation(ui_lang, "SPEAK.ffmpeg_unavailable"),
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
                        get_translation(ui_lang, "SPEAK.ffmpeg_error", error=error_message),
                        ephemeral=True
                    )
                    # Send the file as fallback
                    await interaction.channel.send(
                        get_translation(ui_lang, "SPEAK.playback_failed_fallback"),
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
                await interaction.followup.send(
                    get_translation(ui_lang, "SPEAK.playing_audio", channel=voice_channel.name), 
                    ephemeral=True
                )
                
            except Exception as e:
                # Get detailed error information
                error_message = str(e)
                await interaction.followup.send(
                    get_translation(ui_lang, "SPEAK.detailed_error", error=error_message),
                    ephemeral=True
                )
                # Send the file as fallback
                await interaction.channel.send(
                    get_translation(ui_lang, "SPEAK.playback_failed_fallback"),
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
                get_translation(ui_lang, "SPEAK.error_general", error=str(e)),
                ephemeral=True
            )
            
        # Close the BytesIO buffer
        mp3_fp.close()
        
    except Exception as e:
        if not interaction.response.is_done():
            await interaction.response.send_message(
                get_translation(ui_lang, "SPEAK.error_general", error=str(e)),
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                get_translation(ui_lang, "SPEAK.error_general", error=str(e)),
                ephemeral=True
            )


async def create_and_send_speak_embeds(
    interaction: discord.Interaction,
    original_text: str,
    translated_text: str,
    source_code: str,
    target_code: str,
    tier: str,
    points_awarded: int,
    limits: dict,
    ui_lang: str,
    user_id: int
):
    """Create and send speak translation embeds with proper truncation and splitting"""
    
    # Get language names and flags
    source_name = get_translation(ui_lang, f"LANGUAGES.{source_code}", default=languages.get(source_code, source_code))
    target_name = get_translation(ui_lang, f"LANGUAGES.{target_code}", default=languages.get(target_code, target_code))
    source_flag = flag_mapping.get(source_code, '🌐')
    target_flag = flag_mapping.get(target_code, '🌐')
    
    # Tier colors
    tier_colors = {'free': 0x95a5a6, 'basic': 0x3498db, 'premium': 0xf39c12, 'pro': 0x9b59b6}
    embed_color = tier_colors.get(tier, discord.Color.greyple())
    
    # Calculate footer text
    footer_key = f"SPEAK.footer_{tier}"
    if interaction.guild:
        footer_text = get_translation(ui_lang, footer_key) + " " + get_translation(ui_lang, "SPEAK.footer_server", server=interaction.guild.name)
    else:
        footer_text = get_translation(ui_lang, footer_key) + " " + get_translation(ui_lang, "SPEAK.footer_dm")
    
    footer_text = footer_text[:2048]  # Discord footer limit
    
    # Field names (truncated to Discord's 256 character limit)
    original_field_name = get_translation(ui_lang, "SPEAK.original_field", flag=source_flag, language=source_name)[:256]
    translation_field_name = get_translation(ui_lang, "SPEAK.translation_field", flag=target_flag, language=target_name)[:256]
    points_field_name = get_translation(ui_lang, "SPEAK.points_field")[:256]
    points_field_value = get_translation(ui_lang, "SPEAK.points_value", points=points_awarded)[:1024]
    
    # Helper function to add field and handle embed limits
    def add_field_to_embed(embed_obj, field_name, field_value, field_counter):
        """Helper function to add field and handle embed limits"""
        # Check if current embed can hold another field (Discord limit is 25 fields per embed)
        if field_counter >= 25:
            return None, field_counter  # Signal that we need a new embed
        
        embed_obj.add_field(
            name=field_name,
            value=field_value,
            inline=False
        )
        return embed_obj, field_counter + 1
    
    # Split texts into chunks that fit Discord's 1024 character field limit
    def split_text_for_fields(text, max_length=1020):  # Leave some room for safety
        """Split text into chunks that fit in Discord embed fields"""
        if len(text) <= max_length:
            return [text]
        
        chunks = []
        current_pos = 0
        
        while current_pos < len(text):
            if current_pos + max_length >= len(text):
                # Last chunk
                chunks.append(text[current_pos:])
                break
            
            # Find a good breaking point (prefer word boundaries)
            chunk_end = current_pos + max_length
            
            # Look for word boundary within last 100 characters
            best_break = chunk_end
            for i in range(chunk_end - 100, chunk_end):
                if i > current_pos and text[i] in [' ', '\n', '\t', '.', ',', '!', '?', ';']:
                    best_break = i + 1
                    break
            
            chunks.append(text[current_pos:best_break])
            current_pos = best_break
        
        return chunks
    
    # Create the main embed
    main_embed = discord.Embed(
        title=get_translation(ui_lang, "SPEAK.title")[:256],
        color=embed_color
    )
    
    embeds_to_send = [main_embed]
    current_embed = main_embed
    field_count = 0
    
    # Add original text fields (if not hidden)
    if user_id not in hidden_sessions:
        original_chunks = split_text_for_fields(original_text)
        for i, chunk in enumerate(original_chunks):
            field_name = original_field_name if i == 0 else f"{original_field_name} (continued {i+1})"
            
            result, field_count = add_field_to_embed(current_embed, field_name, chunk, field_count)
            if result is None:
                # Need a new embed
                new_embed = discord.Embed(
                    title=f"{get_translation(ui_lang, 'SPEAK.title')} (continued)",
                    color=embed_color
                )
                embeds_to_send.append(new_embed)
                current_embed = new_embed
                field_count = 0
                current_embed.add_field(name=field_name, value=chunk, inline=False)
                field_count += 1
    
    # Add translation fields
    translation_chunks = split_text_for_fields(translated_text)
    for i, chunk in enumerate(translation_chunks):
        field_name = translation_field_name if i == 0 else f"{translation_field_name} (continued {i+1})"
        
        result, field_count = add_field_to_embed(current_embed, field_name, chunk, field_count)
        if result is None:
            # Need a new embed
            new_embed = discord.Embed(
                title=f"{get_translation(ui_lang, 'SPEAK.title')} (continued)",
                color=embed_color
            )
            embeds_to_send.append(new_embed)
            current_embed = new_embed
            field_count = 0
            current_embed.add_field(name=field_name, value=chunk, inline=False)
            field_count += 1
    
    # Add points field to the last embed
    result, field_count = add_field_to_embed(current_embed, points_field_name, points_field_value, field_count)
    if result is None:
        # Need a new embed for points field
        new_embed = discord.Embed(
            title=f"{get_translation(ui_lang, 'SPEAK.title')} (continued)",
            color=embed_color
        )
        embeds_to_send.append(new_embed)
        current_embed = new_embed
        current_embed.add_field(name=points_field_name, value=points_field_value, inline=True)
    
    # Set footer on the last embed
    embeds_to_send[-1].set_footer(text=footer_text)
    
    # Send all embeds
    await interaction.followup.send(embed=embeds_to_send[0], ephemeral=True)
    
    # Send additional embeds as followups if needed
    for additional_embed in embeds_to_send[1:]:
        await interaction.followup.send(embed=additional_embed, ephemeral=True)


# Add autocomplete
translate_and_speak_voice.autocomplete('source_lang')(translated_language_autocomplete)
translate_and_speak_voice.autocomplete('target_lang')(translated_language_autocomplete)

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
    
    # Get user's UI language
    ui_lang = await get_user_ui_language(user_id)
    
    hidden_sessions.add(user_id)
    await interaction.response.send_message(
        get_translation(ui_lang, "HIDE.success_message"), 
        ephemeral=True
    )

@tree.command(name="show", description="Show original speech")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def show_speech(interaction: discord.Interaction):
    user_id = interaction.user.id
    
    # Get user's UI language
    ui_lang = await get_user_ui_language(user_id)
    
    hidden_sessions.discard(user_id)
    await interaction.response.send_message(
        get_translation(ui_lang, "SHOW.success_message"), 
        ephemeral=True
    )

@tree.command(name="stop", description="Stop your active translation sessions")
async def stop_voice_translation(interaction: discord.Interaction):
    """Stop the active voice translation session and/or auto-translate with detailed stats"""
    try:
        await track_command_usage(interaction)
        
        user_id = interaction.user.id
        guild_id = interaction.guild_id
        
        # Get user's UI language
        ui_lang = await get_user_ui_language(user_id)
        
        # Check what sessions are active
        has_voice_session = guild_id in voice_translation_sessions
        has_auto_translate = user_id in auto_translate_users
        
        if not has_voice_session and not has_auto_translate:
            embed = discord.Embed(
                title=get_translation(ui_lang, "STOP.no_session_title"),
                description=get_translation(ui_lang, "STOP.no_session_desc"),
                color=0xFF6B6B
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Handle auto-translate stopping
        auto_translate_stopped = False
        if has_auto_translate:
            auto_settings = auto_translate_users[user_id]
            # Check if auto-translate is active in this guild/channel
            if auto_settings['guild_id'] == guild_id and auto_settings['channel_id'] == interaction.channel_id:
                del auto_translate_users[user_id]
                auto_translate_stopped = True
        
        # Handle voice session stopping
        voice_session_data = None
        if has_voice_session:
            session = voice_translation_sessions[guild_id]
            
            # Check if user has permission to stop (original user or admin)
            original_user = session.get('initiating_user_id')
            
            if (user_id != original_user and
                not interaction.user.guild_permissions.administrator and
                not interaction.user.guild_permissions.manage_guild):
                
                # If they can stop auto-translate but not voice, handle that
                if auto_translate_stopped:
                    embed = discord.Embed(
                        title=get_translation(ui_lang, "STOP.auto_translate_stopped_title"),
                        description=get_translation(ui_lang, "STOP.auto_translate_stopped_desc"),
                        color=0x00FF00
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
                else:
                    embed = discord.Embed(
                        title=get_translation(ui_lang, "STOP.permission_denied_title"),
                        description=get_translation(ui_lang, "STOP.permission_denied_desc",
                                                  original_user=original_user),
                        color=0xFF6B6B
                    )
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                    return
            
            await interaction.response.defer(ephemeral=True)
            
            # Collect session information before stopping
            session_type = session.get('type', 'voicechat')
            start_time = session.get('start_time', time.time())
            duration_seconds = int(time.time() - start_time)
            voice_channel = session.get('channel')
            languages = session.get('languages', [])
            
            # Store session data for the embed
            voice_session_data = {
                'type': session_type,
                'duration': duration_seconds,
                'channel': voice_channel,
                'languages': languages,
                'original_user': original_user
            }
            
            # Get user info
            try:
                original_user_obj = await interaction.guild.fetch_member(original_user) if original_user else None
                original_username = original_user_obj.display_name if original_user_obj else get_translation(ui_lang, "STOP.unknown_user")
            except:
                original_username = get_translation(ui_lang, "STOP.user_id_format", user_id=original_user)
            
            voice_session_data['original_username'] = original_username
            
            # Stop the session (same cleanup logic as before)
            cleanup_success = True
            cleanup_errors = []
            
            try:
                voice_client = session.get('voice_client')
                sink = session.get('sink')
                
                # Send voicechat2 session stats if it's an enhanced session
                if session_type in ['voicechat2', 'enhanced_v2']:
                    try:
                        await send_voicechat2_session_stats(guild_id, "manual_stop", user_id)
                    except Exception as e:
                        cleanup_errors.append(get_translation(ui_lang, "STOP.cleanup_error_stats", error=str(e)))
                
                # Stop listening if voice client exists and is listening
                if voice_client and hasattr(voice_client, 'is_listening'):
                    try:
                        if voice_client.is_listening():
                            voice_client.stop_listening()
                    except Exception as e:
                        cleanup_errors.append(get_translation(ui_lang, "STOP.cleanup_error_listening", error=str(e)))
                
                # Clean up sink properly
                if sink and hasattr(sink, 'cleanup'):
                    try:
                        if asyncio.iscoroutinefunction(sink.cleanup):
                            await sink.cleanup()
                        else:
                            # Run sync cleanup in executor to avoid blocking
                            loop = asyncio.get_event_loop()
                            await loop.run_in_executor(None, sink.cleanup)
                    except Exception as e:
                        cleanup_errors.append(get_translation(ui_lang, "STOP.cleanup_error_sink", error=str(e)))
                
                # Stop playing and disconnect
                if voice_client:
                    try:
                        if hasattr(voice_client, 'is_playing') and voice_client.is_playing():
                            voice_client.stop()
                    except Exception as e:
                        cleanup_errors.append(get_translation(ui_lang, "STOP.cleanup_error_playing", error=str(e)))
                    
                    try:
                        if hasattr(voice_client, 'is_connected') and voice_client.is_connected():
                            await voice_client.disconnect()
                    except Exception as e:
                        cleanup_errors.append(get_translation(ui_lang, "STOP.cleanup_error_disconnect", error=str(e)))
                
                # Remove session
                del voice_translation_sessions[guild_id]
                
            except Exception as e:
                logger.error(f"Error stopping voice session: {e}")
                cleanup_success = False
                cleanup_errors.append(get_translation(ui_lang, "STOP.cleanup_error_general", error=str(e)))
                # Force cleanup
                if guild_id in voice_translation_sessions:
                    del voice_translation_sessions[guild_id]
            
            voice_session_data['cleanup_success'] = cleanup_success
            voice_session_data['cleanup_errors'] = cleanup_errors
        else:
            # Only auto-translate was stopped
            await interaction.response.defer(ephemeral=True)
        
        # Create the response embed based on what was stopped
        if voice_session_data and auto_translate_stopped:
            # Both were stopped
            embed_title = get_translation(ui_lang, "STOP.both_stopped_title")
            embed_color = 0x00FF00
        elif voice_session_data:
            # Only voice session was stopped
            cleanup_success = voice_session_data['cleanup_success']
            cleanup_errors = voice_session_data['cleanup_errors']
            
            if cleanup_success and not cleanup_errors:
                embed_color = 0x00FF00  # Green for success
                embed_title = get_translation(ui_lang, "STOP.success_title")
            elif cleanup_errors:
                embed_color = 0xFFA500  # Orange for warnings
                embed_title = get_translation(ui_lang, "STOP.warning_title")
            else:
                embed_color = 0xFF6B6B  # Red for errors
                embed_title = get_translation(ui_lang, "STOP.error_title")
        else:
            # Only auto-translate was stopped
            embed_title = get_translation(ui_lang, "STOP.auto_translate_stopped_title")
            embed_color = 0x00FF00
        
        embed = discord.Embed(
            title=embed_title,
            description=get_translation(ui_lang, "STOP.session_terminated", user=interaction.user.mention),
            color=embed_color,
            timestamp=datetime.utcnow()
        )
        
        # Add auto-translate info if it was stopped
        if auto_translate_stopped:
            embed.add_field(
                name=get_translation(ui_lang, "STOP.auto_translate_field"),
                value=get_translation(ui_lang, "STOP.auto_translate_disabled"),
                inline=False
            )
        
        # Add voice session details if applicable
        if voice_session_data:
            duration_seconds = voice_session_data['duration']
            
            # Session Duration Info
            duration_str = format_seconds(duration_seconds)
            embed.add_field(
                name=get_translation(ui_lang, "STOP.duration_field"),
                value=duration_str,
                inline=True
            )
            
            # Session Type
            session_type = voice_session_data['type']
            session_type_key = f"STOP.session_type_{session_type}"
            session_type_display = get_translation(ui_lang, session_type_key, fallback=f"🎤 {session_type.title()}")
            
            embed.add_field(
                name=get_translation(ui_lang, "STOP.session_type_field"),
                value=session_type_display,
                inline=True
            )
            
            # Voice Channel
            voice_channel = voice_session_data['channel']
            if voice_channel:
                embed.add_field(
                    name=get_translation(ui_lang, "STOP.voice_channel_field"),
                    value=f"#{voice_channel.name}",
                    inline=True
                )
            
            # Languages - Handle languages as a list properly
            languages = voice_session_data['languages']
            if languages and isinstance(languages, list) and len(languages) >= 2:
                source_lang = languages[0] if languages[0] != 'auto' else 'auto'
                target_lang = languages[1]
                
                # Get language names and flags
                try:
                    source_name = languages.get(source_lang, source_lang)
                    target_name = languages.get(target_lang, target_lang)
                    source_flag = flag_mapping.get(source_lang, '🌐') if source_lang != 'auto' else '🔍'
                    target_flag = flag_mapping.get(target_lang, '🌐')
                    
                    embed.add_field(
                        name=get_translation(ui_lang, "STOP.translation_direction_field"),
                        value=f"{source_flag} {source_name} → {target_flag} {target_name}",
                        inline=False
                    )
                except Exception as e:
                    logger.error(f"Error formatting languages: {e}")
                    # Fallback display
                    embed.add_field(
                        name=get_translation(ui_lang, "STOP.translation_direction_field"),
                        value=f"{source_lang} → {target_lang}",
                        inline=False
                    )
            
            # Original User Info
            original_user = voice_session_data['original_user']
            original_username = voice_session_data['original_username']
            embed.add_field(
                name=get_translation(ui_lang, "STOP.started_by_field"),
                value=get_translation(ui_lang, "STOP.started_by_value", username=original_username, user_id=original_user),
                inline=True
            )
            
            # Session Statistics
            if duration_seconds > 0:
                # Calculate some basic stats
                minutes = duration_seconds // 60
                hours = minutes // 60
                
                stats_text = []
                if hours > 0:
                    hour_text = get_translation(ui_lang, "STOP.hours_plural" if hours != 1 else "STOP.hours_singular", count=hours)
                    stats_text.append(f"🕐 {hour_text}")
                if minutes % 60 > 0:
                    minute_text = get_translation(ui_lang, "STOP.minutes_plural" if minutes % 60 != 1 else "STOP.minutes_singular", count=minutes % 60)
                    stats_text.append(f"⏰ {minute_text}")
                if duration_seconds % 60 > 0 and duration_seconds < 300:  # Show seconds only for short sessions
                    second_text = get_translation(ui_lang, "STOP.seconds_plural" if duration_seconds % 60 != 1 else "STOP.seconds_singular", count=duration_seconds % 60)
                    stats_text.append(f"⏱️ {second_text}")
                
                if stats_text:
                    embed.add_field(
                        name=get_translation(ui_lang, "STOP.detailed_duration_field"),
                        value=" • ".join(stats_text),
                        inline=False
                    )
            
            # Usage tracking (if available)
            try:
                if original_user:
                    daily_usage = await db.get_daily_usage(original_user)
                    if daily_usage and isinstance(daily_usage, dict):
                        embed.add_field(
                            name=get_translation(ui_lang, "STOP.todays_usage_field"),
                            value=get_translation(ui_lang, "STOP.todays_usage_value",
                                                text_chars=daily_usage.get('text_chars', 0),
                                                voice_time=format_seconds(daily_usage.get('voice_seconds', 0)),
                                                translations=daily_usage.get('translations', 0)),
                            inline=True
                        )
            except Exception as e:
                logger.error(f"Error getting usage stats: {e}")
            
            # Points awarded (if applicable)
            if original_user and duration_seconds > 60:  # Only for sessions longer than 1 minute
                try:
                    # Calculate points based on session duration
                    base_points = max(1, duration_seconds // 60)  # 1 point per minute
                    
                    # Get user tier for multiplier
                    current_tier = tier_handler.get_user_tier(original_user)
                    tier_multipliers = {'free': 1, 'basic': 1.5, 'premium': 2, 'pro': 3}
                    multiplier = tier_multipliers.get(current_tier, 1)
                    
                    final_points = int(base_points * multiplier)
                    
                    # Award the points
                    reward_db.add_points(original_user, final_points, f"Voice session completion ({duration_str})")
                    
                    embed.add_field(
                        name=get_translation(ui_lang, "STOP.points_awarded_field"),
                                                value=get_translation(ui_lang, "STOP.points_awarded_value",
                                            points=final_points, tier=current_tier.title()),
                        inline=True
                    )
                except Exception as e:
                    logger.error(f"Error awarding session points: {e}")
            
            # Cleanup warnings/errors
            cleanup_errors = voice_session_data.get('cleanup_errors', [])
            if cleanup_errors:
                embed.add_field(
                    name=get_translation(ui_lang, "STOP.cleanup_issues_field"),
                    value="\n".join([f"• {error}" for error in cleanup_errors[:3]]),  # Limit to 3 errors
                    inline=False
                )
        
        # Footer with helpful info
        if auto_translate_stopped and voice_session_data:
            footer_text = get_translation(ui_lang, "STOP.footer_both_stopped")
        elif auto_translate_stopped:
            footer_text = get_translation(ui_lang, "STOP.footer_auto_stopped")
        else:
            footer_text = get_translation(ui_lang, "STOP.footer_text")
        
        embed.set_footer(
            text=footer_text,
            icon_url=interaction.user.display_avatar.url
        )
        
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error in stop voice command: {e}")
        
        # Get UI language for error message
        try:
            ui_lang = await get_user_ui_language(interaction.user.id)
        except:
            ui_lang = 'en'
        
        # Fallback error embed
        error_embed = discord.Embed(
            title=get_translation(ui_lang, "STOP.error_stopping_title"),
            description=get_translation(ui_lang, "STOP.error_stopping_desc", error=str(e)),
            color=0xFF0000,
            timestamp=datetime.utcnow()
        )
        error_embed.set_footer(text=get_translation(ui_lang, "STOP.error_footer"))
        
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
        else:
            await interaction.followup.send(embed=error_embed, ephemeral=True)

def format_seconds(seconds):
    """Format seconds into a human-readable duration string"""
    # Handle special cases
    if seconds == float('inf'):
        return "Unlimited"
    if seconds <= 0 or seconds != seconds:  # Check for NaN or negative
        return "0s"
    
    # Convert to int to avoid decimal issues
    seconds = int(seconds)
    
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        minutes = seconds // 60
        remaining_seconds = seconds % 60
        if remaining_seconds == 0:
            return f"{minutes}m"
        else:
            return f"{minutes}m {remaining_seconds}s"
    else:
        hours = seconds // 3600
        remaining_minutes = (seconds % 3600) // 60
        remaining_seconds = seconds % 60
        
        result = f"{hours}h"
        if remaining_minutes > 0:
            result += f" {remaining_minutes}m"
        if remaining_seconds > 0 and hours == 0:  # Only show seconds if less than an hour
            result += f" {remaining_seconds}s"
        
        return result


# Update the auto_translate command to use the new limits
# Fixed /autotranslate command with proper database integration
@tree.command(name="autotranslate", description="Automatically translate all your messages")
@app_commands.describe(
    source_lang="Source language (type to search, or 'auto' for detection)",
    target_lang="Target language (type to search)")
async def auto_translate(
    interaction: discord.Interaction,
    source_lang: str,
    target_lang: str):
    
    try:
        await track_command_usage(interaction)
        
        user_id = interaction.user.id
        guild_id = interaction.guild_id
        
        # Get user's UI language
        ui_lang = await get_user_ui_language(user_id)
        
        # Convert language inputs to codes
        source_code = "auto" if source_lang.lower() == "auto" else get_language_code(source_lang)
        target_code = get_language_code(target_lang)
        if target_code == "auto":
            await interaction.response.send_message(
                get_translation(ui_lang, "AUTO.error_auto_not_allowed_for_target"),
                ephemeral=True
            )
            return
        
        # Check channel permissions if in a guild
        if interaction.guild:
            allowed = await db.is_translation_allowed(
                interaction.guild.id,
                interaction.channel.id,
                "text",
                target_code
            )
            if not allowed:
                embed = discord.Embed(
                    title=get_translation(ui_lang, "AUTOTRANSLATE.error_not_allowed_title"),
                    description=get_translation(ui_lang, "AUTOTRANSLATE.error_not_allowed_desc"),
                    color=0xFF6B6B
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        
        # Validate language codes
        if source_lang.lower() != "auto" and not source_code:
            embed = discord.Embed(
                title=get_translation(ui_lang, "AUTOTRANSLATE.error_invalid_source_title"),
                description=get_translation(ui_lang, "AUTOTRANSLATE.error_invalid_source_desc", 
                                          language=source_lang),
                color=0xFF6B6B
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if not target_code:
            embed = discord.Embed(
                title=get_translation(ui_lang, "AUTOTRANSLATE.error_invalid_target_title"),
                description=get_translation(ui_lang, "AUTOTRANSLATE.error_invalid_target_desc", 
                                          language=target_lang),
                color=0xFF6B6B
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Create/update user in database
        await db.get_or_create_user(user_id, interaction.user.display_name)
        
        # Check if user already has auto-translate enabled
        already_enabled = user_id in auto_translate_users
        if already_enabled:
            old_settings = auto_translate_users[user_id]
            # Check if it's the same settings
            if (old_settings['source'] == source_code and 
                old_settings['target'] == target_code and
                old_settings['guild_id'] == guild_id and
                old_settings['channel_id'] == interaction.channel_id):
                
                embed = discord.Embed(
                    title=get_translation(ui_lang, "AUTOTRANSLATE.already_enabled_title"),
                    description=get_translation(ui_lang, "AUTOTRANSLATE.already_enabled_desc"),
                    color=0xFFA500
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        
        # Store user's auto-translation preferences
        auto_translate_users[user_id] = {
            'source': source_code,
            'target': target_code,
            'guild_id': guild_id,
            'channel_id': interaction.channel_id
        }
        
        # Create and send autotranslate setup embed
        await create_and_send_autotranslate_embed(
            interaction=interaction,
            source_code=source_code,
            target_code=target_code,
            already_enabled=already_enabled,
            ui_lang=ui_lang,
            user_id=user_id
        )
        
    except Exception as e:
        logger.error(f"Error in autotranslate command: {e}")
        
        # Get UI language for error message
        try:
            ui_lang = await get_user_ui_language(interaction.user.id)
        except:
            ui_lang = 'en'
        
        error_embed = discord.Embed(
            title=get_translation(ui_lang, "AUTOTRANSLATE.error_general_title"),
            description=get_translation(ui_lang, "AUTOTRANSLATE.error_general_desc", error=str(e)),
            color=0xFF0000
        )
        
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
        else:
            await interaction.followup.send(embed=error_embed, ephemeral=True)


async def create_and_send_autotranslate_embed(
    interaction: discord.Interaction,
    source_code: str,
    target_code: str,
    already_enabled: bool,
    ui_lang: str,
    user_id: int
):
    """Create and send autotranslate setup embed with proper truncation and splitting"""
    
    # Get proper language names and flags for display
    source_display = get_translation(ui_lang, "AUTOTRANSLATE.auto_detect") if source_code == "auto" else languages.get(source_code, source_code)
    target_display = languages.get(target_code, target_code)
    source_flag = '🔍' if source_code == "auto" else flag_mapping.get(source_code, '🌐')
    target_flag = flag_mapping.get(target_code, '🌐')
    
    # Get user tier and limits
    current_tier = tier_handler.get_user_tier(user_id)
    limits = tier_handler.get_limits(user_id)
    
    # Helper function to add field and handle embed limits
    def add_field_to_embed(embed_obj, field_name, field_value, field_counter):
        """Helper function to add field and handle embed limits"""
        # Check if current embed can hold another field (Discord limit is 25 fields per embed)
        if field_counter >= 25:
            return None, field_counter  # Signal that we need a new embed
        
        embed_obj.add_field(
            name=field_name[:256],  # Discord field name limit
            value=field_value[:1024],  # Discord field value limit
            inline=False
        )
        return embed_obj, field_counter + 1
    
    # Create the main embed
    main_embed = discord.Embed(
        title=get_translation(ui_lang, "AUTOTRANSLATE.enabled_title")[:256],
        description=get_translation(ui_lang, "AUTOTRANSLATE.enabled_desc")[:4096],
        color=0x00FF00,
        timestamp=datetime.utcnow()
    )
    
    embeds_to_send = [main_embed]
    current_embed = main_embed
    field_count = 0
    
    # Translation flow field
    translation_flow_value = f"{source_flag} **{source_display}** ➜ {target_flag} **{target_display}**"
    result, field_count = add_field_to_embed(
        current_embed,
        get_translation(ui_lang, "AUTOTRANSLATE.translation_flow_field"),
        translation_flow_value,
        field_count
    )
    if result is None:
        new_embed = discord.Embed(
            title=f"{get_translation(ui_lang, 'AUTOTRANSLATE.enabled_title')} (continued)",
            color=0x00FF00
        )
        embeds_to_send.append(new_embed)
        current_embed = new_embed
        field_count = 0
        current_embed.add_field(
            name=get_translation(ui_lang, "AUTOTRANSLATE.translation_flow_field")[:256],
            value=translation_flow_value[:1024],
            inline=False
        )
        field_count += 1
    
    # Channel info field
    channel_value = f"#{interaction.channel.name}"
    result, field_count = add_field_to_embed(
        current_embed,
        get_translation(ui_lang, "AUTOTRANSLATE.active_channel_field"),
        channel_value,
        field_count
    )
    if result is None:
        new_embed = discord.Embed(
            title=f"{get_translation(ui_lang, 'AUTOTRANSLATE.enabled_title')} (continued)",
            color=0x00FF00
        )
        embeds_to_send.append(new_embed)
        current_embed = new_embed
        field_count = 0
        current_embed.add_field(
            name=get_translation(ui_lang, "AUTOTRANSLATE.active_channel_field")[:256],
            value=channel_value[:1024],
            inline=True
        )
        field_count += 1
    
    # Your tier field
    tier_emojis = {'free': '🆓', 'basic': '🥉', 'premium': '🥈', 'pro': '🥇'}
    
    if current_tier == 'pro':
        limit_text = get_translation(ui_lang, "AUTOTRANSLATE.unlimited_limit")
    else:
        limit_text = get_translation(ui_lang, "AUTOTRANSLATE.character_limit", limit=limits['text_limit'])
    
    tier_value = f"{tier_emojis[current_tier]} **{current_tier.title()}**\n{limit_text}"
    result, field_count = add_field_to_embed(
        current_embed,
        get_translation(ui_lang, "AUTOTRANSLATE.your_tier_field"),
        tier_value,
        field_count
    )
    if result is None:
        new_embed = discord.Embed(
            title=f"{get_translation(ui_lang, 'AUTOTRANSLATE.enabled_title')} (continued)",
            color=0x00FF00
        )
        embeds_to_send.append(new_embed)
        current_embed = new_embed
        field_count = 0
        current_embed.add_field(
            name=get_translation(ui_lang, "AUTOTRANSLATE.your_tier_field")[:256],
            value=tier_value[:1024],
            inline=True
        )
        field_count += 1
    
    # Points earning field
    points_map = {'free': 1, 'basic': 2, 'premium': 3, 'pro': 4}
    points_per_message = points_map[current_tier]
    points_value = get_translation(ui_lang, "AUTOTRANSLATE.points_earning_value", points=points_per_message)
    
    result, field_count = add_field_to_embed(
        current_embed,
        get_translation(ui_lang, "AUTOTRANSLATE.points_earning_field"),
        points_value,
        field_count
    )
    if result is None:
        new_embed = discord.Embed(
            title=f"{get_translation(ui_lang, 'AUTOTRANSLATE.enabled_title')} (continued)",
            color=0x00FF00
        )
        embeds_to_send.append(new_embed)
        current_embed = new_embed
        field_count = 0
        current_embed.add_field(
            name=get_translation(ui_lang, "AUTOTRANSLATE.points_earning_field")[:256],
            value=points_value[:1024],
            inline=True
        )
        field_count += 1
    
    # How it works field
    how_it_works_value = get_translation(ui_lang, "AUTOTRANSLATE.how_it_works_value")
    result, field_count = add_field_to_embed(
        current_embed,
        get_translation(ui_lang, "AUTOTRANSLATE.how_it_works_field"),
        how_it_works_value,
        field_count
    )
    if result is None:
        new_embed = discord.Embed(
            title=f"{get_translation(ui_lang, 'AUTOTRANSLATE.enabled_title')} (continued)",
            color=0x00FF00
        )
        embeds_to_send.append(new_embed)
        current_embed = new_embed
        field_count = 0
        current_embed.add_field(
            name=get_translation(ui_lang, "AUTOTRANSLATE.how_it_works_field")[:256],
            value=how_it_works_value[:1024],
            inline=False
        )
        field_count += 1
    
    # Important notes field
    if current_tier in ['free', 'basic']:
        notes_value = get_translation(ui_lang, "AUTOTRANSLATE.important_notes_limited", 
                                    limit=limits['text_limit'], tier=current_tier)
    else:
        notes_value = get_translation(ui_lang, "AUTOTRANSLATE.important_notes_unlimited")
    
    result, field_count = add_field_to_embed(
        current_embed,
        get_translation(ui_lang, "AUTOTRANSLATE.important_notes_field"),
        notes_value,
        field_count
    )
    if result is None:
        new_embed = discord.Embed(
            title=f"{get_translation(ui_lang, 'AUTOTRANSLATE.enabled_title')} (continued)",
            color=0x00FF00
        )
        embeds_to_send.append(new_embed)
        current_embed = new_embed
        field_count = 0
        current_embed.add_field(
            name=get_translation(ui_lang, "AUTOTRANSLATE.important_notes_field")[:256],
            value=notes_value[:1024],
            inline=False
        )
        field_count += 1
    
    # Status field
    status_text = get_translation(ui_lang, "AUTOTRANSLATE.status_updated") if already_enabled else get_translation(ui_lang, "AUTOTRANSLATE.status_enabled")
    status_value = f"🟢 {status_text}\n⏹️ {get_translation(ui_lang, 'AUTOTRANSLATE.stop_instruction')}"
    
    result, field_count = add_field_to_embed(
        current_embed,
        get_translation(ui_lang, "AUTOTRANSLATE.status_field"),
        status_value,
        field_count
    )
    if result is None:
        new_embed = discord.Embed(
            title=f"{get_translation(ui_lang, 'AUTOTRANSLATE.enabled_title')} (continued)",
            color=0x00FF00
        )
        embeds_to_send.append(new_embed)
        current_embed = new_embed
        field_count = 0
        current_embed.add_field(
            name=get_translation(ui_lang, "AUTOTRANSLATE.status_field")[:256],
            value=status_value[:1024],
            inline=False
        )
        field_count += 1
    
    # Footer with tier-specific info (only on the last embed)
    tier_footers = {
        'free': get_translation(ui_lang, "AUTOTRANSLATE.footer_free"),
        'basic': get_translation(ui_lang, "AUTOTRANSLATE.footer_basic"),
        'premium': get_translation(ui_lang, "AUTOTRANSLATE.footer_premium"),
        'pro': get_translation(ui_lang, "AUTOTRANSLATE.footer_pro")
    }
    
    embeds_to_send[-1].set_footer(
        text=tier_footers[current_tier][:2048],
        icon_url=interaction.user.display_avatar.url
    )
    
    # Send all embeds
    await interaction.response.send_message(embed=embeds_to_send[0], ephemeral=True)
    
    # Send additional embeds as followups if needed
    for additional_embed in embeds_to_send[1:]:
        await interaction.followup.send(embed=additional_embed, ephemeral=True)


async def create_and_send_autotranslate_message_embed(
    message: discord.Message,
    original_text: str,
    translated_text: str,
    source_code: str,
    target_code: str,
    ui_lang: str,
    user_id: int,
    current_tier: str,
    limits: dict,
    points_awarded: int
):
    """Create and send auto-translate message embed with proper truncation and splitting"""
    
    # Get proper language names and flags
    source_name = get_translation(ui_lang, f"LANGUAGES.{source_code}", default=languages.get(source_code, source_code))
    target_name = get_translation(ui_lang, f"LANGUAGES.{target_code}", default=languages.get(target_code, target_code))
    source_flag = flag_mapping.get(source_code, '🌐')
    target_flag = flag_mapping.get(target_code, '🌐')
    
    # Split texts into chunks that fit Discord's 1024 character field limit
    def split_text_for_fields(text, max_length=1020):
        """Split text into chunks that fit in Discord embed fields"""
        if len(text) <= max_length:
            return [text]
        
        chunks = []
        current_pos = 0
        
        while current_pos < len(text):
            if current_pos + max_length >= len(text):
                chunks.append(text[current_pos:])
                break
            
            # Find a good breaking point (prefer word boundaries)
            chunk_end = current_pos + max_length
            best_break = chunk_end
            for i in range(chunk_end - 100, chunk_end):
                if i > current_pos and text[i] in [' ', '\n', '\t', '.', ',', '!', '?', ';']:
                    best_break = i + 1
                    break
            
            chunks.append(text[current_pos:best_break])
            current_pos = best_break
        
        return chunks
    
    # Helper function to add field and handle embed limits
    def add_field_to_embed(embed_obj, field_name, field_value, field_counter):
        """Helper function to add field and handle embed limits"""
        if field_counter >= 25:
            return None, field_counter
        
        embed_obj.add_field(
            name=field_name[:256],
            value=field_value[:1024],
            inline=False
        )
        return embed_obj, field_counter + 1
    
    # Create tier-based colors
    tier_colors = {'free': 0x95a5a6, 'basic': 0x3498db, 'premium': 0xf39c12, 'pro': 0x9b59b6}
    embed_color = tier_colors[current_tier]
    
    # Create the main embed
    main_embed = discord.Embed(
        title=get_translation(ui_lang, "AUTOTRANSLATE.message_title")[:256],
        color=embed_color
    )
    
    embeds_to_send = [main_embed]
    current_embed = main_embed
    field_count = 0
    
    # Add original text fields (if not hidden)
    if user_id not in hidden_sessions:
        original_chunks = split_text_for_fields(original_text)
        original_field_name = get_translation(ui_lang, "AUTOTRANSLATE.original_field", flag=source_flag, language=source_name)
        
        for i, chunk in enumerate(original_chunks):
            field_name = original_field_name if i == 0 else f"{original_field_name} (continued {i+1})"
            
            result, field_count = add_field_to_embed(current_embed, field_name, chunk, field_count)
            if result is None:
                new_embed = discord.Embed(
                    title=f"{get_translation(ui_lang, 'AUTOTRANSLATE.message_title')} (continued)",
                    color=embed_color
                )
                embeds_to_send.append(new_embed)
                current_embed = new_embed
                field_count = 0
                current_embed.add_field(name=field_name[:256], value=chunk[:1024], inline=False)
                field_count += 1
    
    # Add translation fields
    translation_chunks = split_text_for_fields(translated_text)
    translation_field_name = get_translation(ui_lang, "AUTOTRANSLATE.translation_field", flag=target_flag, language=target_name)
    
    for i, chunk in enumerate(translation_chunks):
        field_name = translation_field_name if i == 0 else f"{translation_field_name} (continued {i+1})"
        
        result, field_count = add_field_to_embed(current_embed, field_name, chunk, field_count)
        if result is None:
            new_embed = discord.Embed(
                title=f"{get_translation(ui_lang, 'AUTOTRANSLATE.message_title')} (continued)",
                color=embed_color
            )
            embeds_to_send.append(new_embed)
            current_embed = new_embed
            field_count = 0
            current_embed.add_field(name=field_name[:256], value=chunk[:1024], inline=False)
            field_count += 1
    
    # Add points field to the last embed
    points_field_name = get_translation(ui_lang, "AUTOTRANSLATE.points_field")
    points_field_value = get_translation(ui_lang, "AUTOTRANSLATE.points_value", points=points_awarded)
    
    result, field_count = add_field_to_embed(current_embed, points_field_name, points_field_value, field_count)
    if result is None:
        new_embed = discord.Embed(
            title=f"{get_translation(ui_lang, 'AUTOTRANSLATE.message_title')} (continued)",
            color=embed_color
        )
        embeds_to_send.append(new_embed)
        current_embed = new_embed
        current_embed.add_field(name=points_field_name[:256], value=points_field_value[:1024], inline=True)
    
    # Add tier-specific footer to the last embed
    tier_footers = {
        'free': get_translation(ui_lang, "AUTOTRANSLATE.message_footer_free", 
                              current=len(original_text), limit=limits['text_limit']),
        'basic': get_translation(ui_lang, "AUTOTRANSLATE.message_footer_basic", 
                               current=len(original_text), limit=limits['text_limit']),
        'premium': get_translation(ui_lang, "AUTOTRANSLATE.message_footer_premium"),
        'pro': get_translation(ui_lang, "AUTOTRANSLATE.message_footer_pro")
    }
    
    embeds_to_send[-1].set_footer(text=tier_footers[current_tier][:2048])
    
    # Send all embeds
    await message.channel.send(embed=embeds_to_send[0])
    
    # Send additional embeds if needed
    for additional_embed in embeds_to_send[1:]:
        await message.channel.send(embed=additional_embed)


# Add autocomplete
auto_translate.autocomplete('source_lang')(translated_language_autocomplete)
auto_translate.autocomplete('target_lang')(translated_language_autocomplete)


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
        if message.guild and message.guild.id == settings['guild_id'] and message.channel.id == settings['channel_id']:
            try:
                # Get user's UI language
                ui_lang = await get_user_ui_language(user_id)
                
                # Get user tier and limits
                current_tier = tier_handler.get_user_tier(user_id)
                is_premium = current_tier in ['premium', 'pro']
                limits = tier_handler.get_limits(user_id)
                
                # Check text length against limits
                if len(message.content) > limits['text_limit']:
                    # Send a private notification about the limit (only once per day to avoid spam)
                    try:
                        daily_usage = await db.get_daily_usage(user_id)
                        if daily_usage['translations'] == 0:  # First translation attempt today
                            limit_embed = discord.Embed(
                                title=get_translation(ui_lang, "AUTOTRANSLATE.limit_exceeded_title"),
                                description=get_translation(ui_lang, "AUTOTRANSLATE.limit_exceeded_desc",
                                                          length=len(message.content),
                                                          tier=current_tier,
                                                          limit=limits['text_limit']),
                                color=0xFFA500
                            )
                            limit_embed.add_field(
                                name=get_translation(ui_lang, "AUTOTRANSLATE.limit_solutions_field"),
                                value=get_translation(ui_lang, "AUTOTRANSLATE.limit_solutions_value"),
                                inline=False
                            )
                            await message.author.send(embed=limit_embed)
                    except Exception as dm_error:
                        logger.debug(f"Could not send DM to user {user_id}: {dm_error}")
                    return
                
                # Don't translate if the message is a command
                if message.content.startswith('/'):
                    return
                
                # Don't translate very short messages
                if len(message.content.strip()) < 2:
                    return
                
                source_code = settings['source']
                target_code = settings['target']
                
                # If source is auto, detect the language
                if source_code == "auto":
                    try:
                        detected_lang = detect(message.content)
                        source_code = detected_lang
                    except:
                        source_code = "en"  # Fallback to English
                
                # Don't translate if source and target are the same
                if source_code == target_code:
                    return
                
                # Translate the text
                translator = GoogleTranslator(source=source_code, target=target_code)
                translated = translator.translate(message.content)
                
                if not translated or translated.strip() == message.content.strip():
                    return  # Skip if translation failed or is identical
                
                # Award points based on tier (SYNC - no await)
                points_map = {'free': 1, 'basic': 2, 'premium': 3, 'pro': 4}
                points_awarded = points_map[current_tier]
                reward_db.add_points(user_id, points_awarded, f"Auto-translation: {source_code}→{target_code}")
                
                # Track usage in database (ASYNC)
                await db.track_usage(user_id, text_chars=len(message.content))
                
                # Save translation to history (ASYNC)
                await db.save_translation(
                    user_id=user_id,
                    guild_id=message.guild.id,
                    original_text=message.content,
                    translated_text=translated,
                    source_lang=source_code,
                    target_lang=target_code,
                    translation_type="auto"
                )
                
                # Track translation for achievements (SYNC - no await)
                achievement_db.track_translation(user_id, source_code, target_code, is_premium)
                new_achievements = achievement_db.check_achievements(user_id)
                if new_achievements:
                    await send_achievement_notification(client, user_id, new_achievements)
                
                username = message.author.display_name
                
                # Check for uncashed achievements
                uncashed_points, _ = reward_db.get_uncashed_achievement_points(user_id)
                await notify_uncashed_achievements(user_id, username, uncashed_points)
                
                # Create and send the translation embed with proper truncation
                await create_and_send_autotranslate_message_embed(
                    message=message,
                    original_text=message.content,
                    translated_text=translated,
                    source_code=source_code,
                    target_code=target_code,
                    ui_lang=ui_lang,
                    user_id=user_id,
                    current_tier=current_tier,
                    limits=limits,
                    points_awarded=points_awarded
                )
                
            except Exception as e:
                logger.error(f"Auto-translation error for user {user_id}: {e}")
                # Don't send error messages to avoid spam, just log it
    
    return

@tree.command(name="dmtr", description="Translate and send a message to another user")
@app_commands.describe(
    user="User to send the translated message to",
    text="Text to translate and send",
    source_lang="Source language (type to search, or 'auto' for detection)",
    target_lang="Target language (type to search)"
)
async def dm_translate(
    interaction: discord.Interaction,
    user: discord.Member,
    text: str,
    source_lang: str,
    target_lang: str):

    try:
        logger.info(f"DM_TRANSLATE: Starting command for user {interaction.user.id}")
        
        logger.info(f"DM_TRANSLATE: Calling track_command_usage")
        await track_command_usage(interaction)
        logger.info(f"DM_TRANSLATE: track_command_usage completed")

        sender_id = interaction.user.id
        logger.info(f"DM_TRANSLATE: Getting UI language for user {sender_id}")
        ui_lang = await get_user_ui_language(sender_id)
        logger.info(f"DM_TRANSLATE: UI language retrieved: {ui_lang}")

        # Convert language inputs to codes
        logger.info(f"DM_TRANSLATE: Converting language codes - source: {source_lang}, target: {target_lang}")
        source_code = "auto" if source_lang.lower() == "auto" else get_language_code(source_lang)
        target_code = get_language_code(target_lang)
        if target_code == "auto":
            await interaction.response.send_message(
                get_translation(ui_lang, "AUTO.error_auto_not_allowed_for_target"),
                ephemeral=True
            )
            return
        logger.info(f"DM_TRANSLATE: Language codes converted - source_code: {source_code}, target_code: {target_code}")

        # Validate language codes
        if source_lang.lower() != "auto" and not source_code:
            logger.warning(f"DM_TRANSLATE: Invalid source language: {source_lang}")
            embed = discord.Embed(
                title=get_translation(ui_lang, "DMTR.error_invalid_source_title"),
                description=get_translation(ui_lang, "DMTR.error_invalid_source_desc", language=source_lang),
                color=0xFF6B6B
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if not target_code:
            logger.warning(f"DM_TRANSLATE: Invalid target language: {target_lang}")
            embed = discord.Embed(
                title=get_translation(ui_lang, "DMTR.error_invalid_target_title"),
                description=get_translation(ui_lang, "DMTR.error_invalid_target_desc", language=target_lang),
                color=0xFF6B6B
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if user.id == sender_id:
            logger.warning(f"DM_TRANSLATE: User trying to DM themselves: {sender_id}")
            embed = discord.Embed(
                title=get_translation(ui_lang, "DMTR.error_self_dm_title"),
                description=get_translation(ui_lang, "DMTR.error_self_dm_desc"),
                color=0xFFA500
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        if user.bot:
            logger.warning(f"DM_TRANSLATE: User trying to DM a bot: {user.id}")
            embed = discord.Embed(
                title=get_translation(ui_lang, "DMTR.error_bot_dm_title"),
                description=get_translation(ui_lang, "DMTR.error_bot_dm_desc"),
                color=0xFFA500
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        logger.info(f"DM_TRANSLATE: Getting user tier for {sender_id}")
        current_tier = tier_handler.get_user_tier(sender_id)
        logger.info(f"DM_TRANSLATE: User tier: {current_tier}")
        
        logger.info(f"DM_TRANSLATE: Getting limits for user {sender_id}")
        limits = tier_handler.get_limits(sender_id)
        logger.info(f"DM_TRANSLATE: Limits retrieved: {limits}")

        if len(text) > limits['text_limit']:
            logger.warning(f"DM_TRANSLATE: Text too long - {len(text)} > {limits['text_limit']}")
            embed = discord.Embed(
                title=get_translation(ui_lang, "DMTR.error_text_too_long_title"),
                description=get_translation(ui_lang, "DMTR.error_text_too_long_desc", length=len(text), tier=current_tier, limit=limits['text_limit']),
                color=0xFF6B6B
            )
            embed.add_field(
                name=get_translation(ui_lang, "DMTR.upgrade_benefits_field"),
                value=get_translation(ui_lang, "DMTR.upgrade_benefits_value"),
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # CRITICAL: Check if check_usage_limits is async or sync
        logger.info(f"DM_TRANSLATE: About to call check_usage_limits - checking if it's async")
        logger.info(f"DM_TRANSLATE: check_usage_limits function type: {type(tier_handler.check_usage_limits)}")
        
        try:
            import asyncio
            if asyncio.iscoroutinefunction(tier_handler.check_usage_limits):
                logger.info(f"DM_TRANSLATE: check_usage_limits IS async - using await")
                can_translate, limit_message = await tier_handler.check_usage_limits(sender_id, text_chars=len(text))
            else:
                logger.info(f"DM_TRANSLATE: check_usage_limits is NOT async - calling directly")
                can_translate, limit_message = tier_handler.check_usage_limits(sender_id, text_chars=len(text))
            logger.info(f"DM_TRANSLATE: check_usage_limits result - can_translate: {can_translate}, limit_message: {limit_message}")
        except Exception as e:
            logger.error(f"DM_TRANSLATE: ERROR in check_usage_limits call: {e}")
            logger.error(f"DM_TRANSLATE: Exception type: {type(e)}")
            raise e

        if not can_translate:
            logger.warning(f"DM_TRANSLATE: Usage limit reached for user {sender_id}")
            embed = discord.Embed(
                title=get_translation(ui_lang, "DMTR.error_limit_reached_title"),
                description=get_translation(ui_lang, "DMTR.error_limit_reached_desc", message=limit_message),
                color=0xFF6B6B
            )
            embed.add_field(
                name=get_translation(ui_lang, "DMTR.limit_solutions_field"),
                value=get_translation(ui_lang, "DMTR.limit_solutions_value"),
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        logger.info(f"DM_TRANSLATE: Deferring interaction response")
        await interaction.response.defer(ephemeral=True)
        logger.info(f"DM_TRANSLATE: Interaction deferred")
        
        logger.info(f"DM_TRANSLATE: Getting or creating user in database")
        await db.get_or_create_user(sender_id, interaction.user.display_name)
        logger.info(f"DM_TRANSLATE: User database operation completed")

        detected_message = ""
        if source_code == "auto":
            logger.info(f"DM_TRANSLATE: Auto-detecting language for text: {text[:50]}...")
            try:
                source_code = detect(text)
                detected_message = get_translation(ui_lang, "DMTR.detected_suffix")
                logger.info(f"DM_TRANSLATE: Language detected: {source_code}")
            except Exception as e:
                logger.error(f"DM_TRANSLATE: Language detection error: {e}")
                source_code = "en"
                detected_message = get_translation(ui_lang, "DMTR.detection_failed_suffix")

        same_language = source_code == target_code
        logger.info(f"DM_TRANSLATE: Same language check: {same_language}")

        try:
            logger.info(f"DM_TRANSLATE: Starting translation from {source_code} to {target_code}")
            translated_text = text if same_language else GoogleTranslator(source=source_code, target=target_code).translate(text)
            logger.info(f"DM_TRANSLATE: Translation completed")

            if not translated_text.strip():
                raise Exception("Translation returned empty result")

        except Exception as e:
            logger.error(f"DM_TRANSLATE: Translation error: {e}")
            embed = discord.Embed(
                title=get_translation(ui_lang, "DMTR.error_translation_failed_title"),
                description=get_translation(ui_lang, "DMTR.error_translation_failed_desc", error=str(e)),
                color=0xFF6B6B
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        logger.info(f"DM_TRANSLATE: Tracking usage in database")
        await db.track_usage(sender_id, text_chars=len(text))
        logger.info(f"DM_TRANSLATE: Saving translation to database")
        await db.save_translation(sender_id, interaction.guild_id or 0, text, translated_text, source_code, target_code, "dm")
        logger.info(f"DM_TRANSLATE: Database operations completed")

        points_map = {'free': 1, 'basic': 2, 'premium': 3, 'pro': 4}
        points_awarded = points_map.get(current_tier, 1)
        logger.info(f"DM_TRANSLATE: Adding {points_awarded} points for tier {current_tier}")
        reward_db.add_points(sender_id, points_awarded, f"DM translation: {source_code}→{target_code}")

        is_premium = current_tier in ['premium', 'pro']
        logger.info(f"DM_TRANSLATE: Tracking achievement - is_premium: {is_premium}")
        achievement_db.track_translation(sender_id, source_code, target_code, is_premium)
        new_achievements = achievement_db.check_achievements(sender_id)
        
        if new_achievements:
            logger.info(f"DM_TRANSLATE: New achievements found: {new_achievements}")
            # Check if send_achievement_notification is async
            try:
                import asyncio
                if asyncio.iscoroutinefunction(send_achievement_notification):
                    logger.info(f"DM_TRANSLATE: send_achievement_notification IS async - using await")
                    await send_achievement_notification(client, sender_id, new_achievements)
                else:
                    logger.info(f"DM_TRANSLATE: send_achievement_notification is NOT async - calling directly")
                    send_achievement_notification(client, sender_id, new_achievements)
                logger.info(f"DM_TRANSLATE: Achievement notification sent")
            except Exception as e:
                logger.error(f"DM_TRANSLATE: Error sending achievement notification: {e}")

        logger.info(f"DM_TRANSLATE: Getting language names and flags")
        source_name = get_translation(ui_lang, f"LANGUAGES.{source_code}", default=languages.get(source_code, source_code))
        target_name = get_translation(ui_lang, f"LANGUAGES.{target_code}", default=languages.get(target_code, target_code))
        source_flag = flag_mapping.get(source_code, '🌐')
        target_flag = flag_mapping.get(target_code, '🌐')

        try:
            logger.info(f"DM_TRANSLATE: Getting recipient UI language for user {user.id}")
            recipient_ui_lang = await get_user_ui_language(user.id)
            logger.info(f"DM_TRANSLATE: Recipient UI language: {recipient_ui_lang}")
        except Exception as e:
            logger.error(f"DM_TRANSLATE: Error getting recipient UI language: {e}")
            recipient_ui_lang = 'en'

        # Create and send recipient embed with proper truncation
        logger.info(f"DM_TRANSLATE: Creating recipient embeds")
        dm_sent = await create_and_send_recipient_embed(
            user=user,
            interaction=interaction,
            text=text,
            translated_text=translated_text,
            source_code=source_code,
            target_code=target_code,
            source_name=source_name,
            target_name=target_name,
            source_flag=source_flag,
            target_flag=target_flag,
            source_lang=source_lang,
            detected_message=detected_message,
            same_language=same_language,
            recipient_ui_lang=recipient_ui_lang
        )

        # Create and send sender embed with proper truncation
        logger.info(f"DM_TRANSLATE: Creating sender embeds")
        await create_and_send_sender_embed(
            interaction=interaction,
            user=user,
            text=text,
            translated_text=translated_text,
            source_code=source_code,
            target_code=target_code,
            source_name=source_name,
            target_name=target_name,
            source_flag=source_flag,
            target_flag=target_flag,
            same_language=same_language,
            points_awarded=points_awarded,
            current_tier=current_tier,
            limits=limits,
            dm_sent=dm_sent,
            ui_lang=ui_lang
        )

        logger.info(f"DM_TRANSLATE: Command completed successfully")

    except Exception as e:
        logger.error(f"DM_TRANSLATE: MAIN EXCEPTION CAUGHT - Type: {type(e)}, Message: {str(e)}")
        logger.error(f"DM_TRANSLATE: Exception details: {repr(e)}")
        import traceback
        logger.error(f"DM_TRANSLATE: Full traceback: {traceback.format_exc()}")
        
        try:
            ui_lang = await get_user_ui_language(interaction.user.id)
        except Exception as lang_e:
            logger.error(f"DM_TRANSLATE: Error getting UI language in exception handler: {lang_e}")
            ui_lang = 'en'

        error_embed = discord.Embed(
            title=get_translation(ui_lang, "DMTR.error_general_title"),
            description=get_translation(ui_lang, "DMTR.error_general_desc", error=str(e)),
            color=0xFF0000
        )

        try:
            if not interaction.response.is_done():
                logger.info(f"DM_TRANSLATE: Sending error response (initial)")
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
            else:
                logger.info(f"DM_TRANSLATE: Sending error response (followup)")
                await interaction.followup.send(embed=error_embed, ephemeral=True)
        except Exception as response_e:
            logger.error(f"DM_TRANSLATE: Error sending error response: {response_e}")


async def create_and_send_recipient_embed(
    user: discord.Member,
    interaction: discord.Interaction,
    text: str,
    translated_text: str,
    source_code: str,
    target_code: str,
    source_name: str,
    target_name: str,
    source_flag: str,
    target_flag: str,
    source_lang: str,
    detected_message: str,
    same_language: bool,
    recipient_ui_lang: str
) -> bool:
    """Create and send recipient DM embed with proper truncation and splitting"""
    
    # Split texts into chunks that fit Discord's 1024 character field limit
    def split_text_for_fields(text, max_length=1020):
        """Split text into chunks that fit in Discord embed fields"""
        if len(text) <= max_length:
            return [text]
        
        chunks = []
        current_pos = 0
        
        while current_pos < len(text):
            if current_pos + max_length >= len(text):
                chunks.append(text[current_pos:])
                break
            
            # Find a good breaking point (prefer word boundaries)
            chunk_end = current_pos + max_length
            best_break = chunk_end
            for i in range(chunk_end - 100, chunk_end):
                if i > current_pos and text[i] in [' ', '\n', '\t', '.', ',', '!', '?', ';']:
                    best_break = i + 1
                    break
            
            chunks.append(text[current_pos:best_break])
            current_pos = best_break
        
        return chunks
    
    # Helper function to add field and handle embed limits
    def add_field_to_embed(embed_obj, field_name, field_value, field_counter):
        """Helper function to add field and handle embed limits"""
        if field_counter >= 25:
            return None, field_counter
        
        embed_obj.add_field(
            name=field_name[:256],
            value=field_value[:1024],
            inline=False
        )
        return embed_obj, field_counter + 1
    
    # Create the main recipient embed
    main_embed = discord.Embed(
        title=get_translation(recipient_ui_lang, "DMTR.recipient_title", sender=interaction.user.display_name)[:256],
        description=get_translation(recipient_ui_lang, "DMTR.recipient_desc")[:4096],
        color=0x3498db,
        timestamp=datetime.utcnow()
    )
    
    embeds_to_send = [main_embed]
    current_embed = main_embed
    field_count = 0
    
    # Add original text fields
    original_chunks = split_text_for_fields(text)
    source_field_name = get_translation(recipient_ui_lang, "DMTR.original_field", flag=source_flag, language=source_name)
    if source_lang.lower() == "auto":
        source_field_name += detected_message
    
    for i, chunk in enumerate(original_chunks):
        field_name = source_field_name if i == 0 else f"{source_field_name} (continued {i+1})"
        
        result, field_count = add_field_to_embed(current_embed, field_name, chunk, field_count)
        if result is None:
            new_embed = discord.Embed(
                title=f"{get_translation(recipient_ui_lang, 'DMTR.recipient_title', sender=interaction.user.display_name)} (continued)",
                color=0x3498db
            )
            embeds_to_send.append(new_embed)
            current_embed = new_embed
            field_count = 0
            current_embed.add_field(name=field_name[:256], value=chunk[:1024], inline=False)
            field_count += 1
    
    # Add translation fields
    if same_language:
        same_lang_field_name = get_translation(recipient_ui_lang, "DMTR.same_language_field", flag=target_flag, language=target_name)
        same_lang_field_value = get_translation(recipient_ui_lang, "DMTR.same_language_value")
        
        result, field_count = add_field_to_embed(current_embed, same_lang_field_name, same_lang_field_value, field_count)
        if result is None:
            new_embed = discord.Embed(
                title=f"{get_translation(recipient_ui_lang, 'DMTR.recipient_title', sender=interaction.user.display_name)} (continued)",
                color=0x3498db
            )
            embeds_to_send.append(new_embed)
            current_embed = new_embed
            field_count = 0
            current_embed.add_field(name=same_lang_field_name[:256], value=same_lang_field_value[:1024], inline=False)
            field_count += 1
    else:
        translation_chunks = split_text_for_fields(translated_text)
        translation_field_name = get_translation(recipient_ui_lang, "DMTR.translation_field", flag=target_flag, language=target_name)
        
        for i, chunk in enumerate(translation_chunks):
            field_name = translation_field_name if i == 0 else f"{translation_field_name} (continued {i+1})"
            
            result, field_count = add_field_to_embed(current_embed, field_name, chunk, field_count)
            if result is None:
                new_embed = discord.Embed(
                    title=f"{get_translation(recipient_ui_lang, 'DMTR.recipient_title', sender=interaction.user.display_name)} (continued)",
                    color=0x3498db
                )
                embeds_to_send.append(new_embed)
                current_embed = new_embed
                field_count = 0
                current_embed.add_field(name=field_name[:256], value=chunk[:1024], inline=False)
                field_count += 1
    
    # Add server context field if in a guild
    if interaction.guild:
        context_field_name = get_translation(recipient_ui_lang, "DMTR.server_context_field")
        context_field_value = get_translation(recipient_ui_lang, "DMTR.server_context_value", 
                                            server=interaction.guild.name, channel=interaction.channel.name)
        
        result, field_count = add_field_to_embed(current_embed, context_field_name, context_field_value, field_count)
        if result is None:
            new_embed = discord.Embed(
                title=f"{get_translation(recipient_ui_lang, 'DMTR.recipient_title', sender=interaction.user.display_name)} (continued)",
                color=0x3498db
            )
            embeds_to_send.append(new_embed)
            current_embed = new_embed
            field_count = 0
            current_embed.add_field(name=context_field_name[:256], value=context_field_value[:1024], inline=True)
            field_count += 1
    
    # Set footer on the last embed
    embeds_to_send[-1].set_footer(
        text=get_translation(recipient_ui_lang, "DMTR.recipient_footer")[:2048],
        icon_url=interaction.user.display_avatar.url
    )
    
    # Try to send the DM
    try:
        dm_channel = await user.create_dm()
        await dm_channel.send(embed=embeds_to_send[0])
        
        # Send additional embeds if needed
        for additional_embed in embeds_to_send[1:]:
            await dm_channel.send(embed=additional_embed)
        
        return True
    except discord.Forbidden:
        logger.warning(f"DM_TRANSLATE: DM forbidden - user has DMs disabled")
        return False
    except Exception as e:
        logger.error(f"DM_TRANSLATE: Error sending DM: {e}")
        return False


async def create_and_send_sender_embed(
    interaction: discord.Interaction,
    user: discord.Member,
    text: str,
    translated_text: str,
    source_code: str,
    target_code: str,
    source_name: str,
    target_name: str,
    source_flag: str,
    target_flag: str,
    same_language: bool,
    points_awarded: int,
    current_tier: str,
    limits: dict,
    dm_sent: bool,
    ui_lang: str
):
    """Create and send sender response embed with proper truncation and splitting"""
    
    # Split texts into chunks that fit Discord's 1024 character field limit
    def split_text_for_fields(text, max_length=1020):
        """Split text into chunks that fit in Discord embed fields"""
        if len(text) <= max_length:
            return [text]
        
        chunks = []
        current_pos = 0
        
        while current_pos < len(text):
            if current_pos + max_length >= len(text):
                chunks.append(text[current_pos:])
                break
            
            # Find a good breaking point (prefer word boundaries)
            chunk_end = current_pos + max_length
            best_break = chunk_end
            for i in range(chunk_end - 100, chunk_end):
                if i > current_pos and text[i] in [' ', '\n', '\t', '.', ',', '!', '?', ';']:
                    best_break = i + 1
                    break
            
            chunks.append(text[current_pos:best_break])
            current_pos = best_break
        
        return chunks
    
    # Helper function to add field and handle embed limits
    def add_field_to_embed(embed_obj, field_name, field_value, field_counter, inline=False):
        """Helper function to add field and handle embed limits"""
        if field_counter >= 25:
            return None, field_counter
        
        embed_obj.add_field(
            name=field_name[:256],
            value=field_value[:1024],
            inline=inline
        )
        return embed_obj, field_counter + 1
    
    # Create the main sender embed
    embed_color = 0x2ecc71 if dm_sent else 0xFFA500
    main_embed = discord.Embed(
        title=get_translation(ui_lang, "DMTR.success_title" if dm_sent else "DMTR.failed_title", user=user.display_name)[:256],
        description=get_translation(ui_lang, "DMTR.success_desc" if dm_sent else "DMTR.failed_desc")[:4096],
        color=embed_color,
        timestamp=datetime.utcnow()
    )
    
    embeds_to_send = [main_embed]
    current_embed = main_embed
    field_count = 0
    
    # Add original text fields
    original_chunks = split_text_for_fields(text)
    original_field_name = get_translation(ui_lang, "DMTR.original_field", flag=source_flag, language=source_name)
    
    for i, chunk in enumerate(original_chunks):
        field_name = original_field_name if i == 0 else f"{original_field_name} (continued {i+1})"
        
        result, field_count = add_field_to_embed(current_embed, field_name, chunk, field_count)
        if result is None:
            new_embed = discord.Embed(
                title=f"{get_translation(ui_lang, 'DMTR.success_title' if dm_sent else 'DMTR.failed_title', user=user.display_name)} (continued)",
                color=embed_color
            )
            embeds_to_send.append(new_embed)
            current_embed = new_embed
            field_count = 0
            current_embed.add_field(name=field_name[:256], value=chunk[:1024], inline=False)
            field_count += 1
    
    # Add translation fields
    if same_language:
        same_lang_field_name = get_translation(ui_lang, "DMTR.same_language_field", flag=target_flag, language=target_name)
        same_lang_field_value = get_translation(ui_lang, "DMTR.same_language_value")
        
        result, field_count = add_field_to_embed(current_embed, same_lang_field_name, same_lang_field_value, field_count)
        if result is None:
            new_embed = discord.Embed(
                title=f"{get_translation(ui_lang, 'DMTR.success_title' if dm_sent else 'DMTR.failed_title', user=user.display_name)} (continued)",
                color=embed_color
            )
            embeds_to_send.append(new_embed)
            current_embed = new_embed
            field_count = 0
            current_embed.add_field(name=same_lang_field_name[:256], value=same_lang_field_value[:1024], inline=False)
            field_count += 1
    else:
        translation_chunks = split_text_for_fields(translated_text)
        translation_field_name = get_translation(ui_lang, "DMTR.translation_field", flag=target_flag, language=target_name)
        
        for i, chunk in enumerate(translation_chunks):
            field_name = translation_field_name if i == 0 else f"{translation_field_name} (continued {i+1})"
            
            result, field_count = add_field_to_embed(current_embed, field_name, chunk, field_count)
            if result is None:
                new_embed = discord.Embed(
                    title=f"{get_translation(ui_lang, 'DMTR.success_title' if dm_sent else 'DMTR.failed_title', user=user.display_name)} (continued)",
                    color=embed_color
                )
                embeds_to_send.append(new_embed)
                current_embed = new_embed
                field_count = 0
                current_embed.add_field(name=field_name[:256], value=chunk[:1024], inline=False)
                field_count += 1
    
    # Add points field
    points_field_name = get_translation(ui_lang, "DMTR.points_field")
    points_field_value = get_translation(ui_lang, "DMTR.points_value", points=points_awarded)
    
    result, field_count = add_field_to_embed(current_embed, points_field_name, points_field_value, field_count, inline=True)
    if result is None:
        new_embed = discord.Embed(
            title=f"{get_translation(ui_lang, 'DMTR.success_title' if dm_sent else 'DMTR.failed_title', user=user.display_name)} (continued)",
            color=embed_color
        )
        embeds_to_send.append(new_embed)
        current_embed = new_embed
        field_count = 0
        current_embed.add_field(name=points_field_name[:256], value=points_field_value[:1024], inline=True)
        field_count += 1
    
    # Add usage field for free/basic tiers
    if current_tier in ['free', 'basic']:
        usage_field_name = get_translation(ui_lang, "DMTR.usage_field")
        usage_field_value = get_translation(ui_lang, "DMTR.usage_value", current=len(text), limit=limits['text_limit'])
        
        result, field_count = add_field_to_embed(current_embed, usage_field_name, usage_field_value, field_count, inline=True)
        if result is None:
            new_embed = discord.Embed(
                title=f"{get_translation(ui_lang, 'DMTR.success_title' if dm_sent else 'DMTR.failed_title', user=user.display_name)} (continued)",
                color=embed_color
            )
            embeds_to_send.append(new_embed)
            current_embed = new_embed
            field_count = 0
            current_embed.add_field(name=usage_field_name[:256], value=usage_field_value[:1024], inline=True)
            field_count += 1
    
    # Set footer on the last embed
    tier_footers = {
        'free': get_translation(ui_lang, "DMTR.footer_free", current=len(text), limit=limits['text_limit']),
        'basic': get_translation(ui_lang, "DMTR.footer_basic", current=len(text), limit=limits['text_limit']),
        'premium': get_translation(ui_lang, "DMTR.footer_premium"),
        'pro': get_translation(ui_lang, "DMTR.footer_pro")
    }
    embeds_to_send[-1].set_footer(text=tier_footers[current_tier][:2048])
    
    # Send all embeds
    await interaction.followup.send(embed=embeds_to_send[0], ephemeral=True)
    
    # Send additional embeds as followups if needed
    for additional_embed in embeds_to_send[1:]:
        await interaction.followup.send(embed=additional_embed, ephemeral=True)


# Add autocomplete
dm_translate.autocomplete('source_lang')(translated_language_autocomplete)
dm_translate.autocomplete('target_lang')(translated_language_autocomplete)

@tree.command(name="read", description="Translate a message by ID")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(
    message_id="The ID of the message you want to translate",
    target_lang="Target language to translate to (type to search)"
)
async def translate_by_id(
    interaction: discord.Interaction,
    message_id: str,
    target_lang: str):
    
    try:
        await track_command_usage(interaction)
        
        user_id = interaction.user.id
        
        # Get user's UI language
        ui_lang = await get_user_ui_language(user_id)
        
        # Validate and fetch message
        try:
            message_to_translate = await interaction.channel.fetch_message(int(message_id))
        except ValueError:
            embed = discord.Embed(
                title=get_translation(ui_lang, "READ.error_invalid_id_title"),
                description=get_translation(ui_lang, "READ.error_invalid_id_desc"),
                color=0xFF6B6B
            )
            embed.add_field(
                name=get_translation(ui_lang, "READ.how_to_get_id_field"),
                value=get_translation(ui_lang, "READ.how_to_get_id_value"),
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        except discord.NotFound:
            embed = discord.Embed(
                title=get_translation(ui_lang, "READ.error_message_not_found_title"),
                description=get_translation(ui_lang, "READ.error_message_not_found_desc"),
                color=0xFF6B6B
            )
            embed.add_field(
                name=get_translation(ui_lang, "READ.troubleshooting_field"),
                value=get_translation(ui_lang, "READ.troubleshooting_value"),
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        except discord.Forbidden:
            embed = discord.Embed(
                title=get_translation(ui_lang, "READ.error_no_permission_title"),
                description=get_translation(ui_lang, "READ.error_no_permission_desc"),
                color=0xFF6B6B
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if message has content
        if not message_to_translate.content or not message_to_translate.content.strip():
            embed = discord.Embed(
                title=get_translation(ui_lang, "READ.error_no_content_title"),
                description=get_translation(ui_lang, "READ.error_no_content_desc"),
                color=0xFFA500
            )
            
            # Check if message has embeds or attachments
            content_types = []
            if message_to_translate.embeds:
                content_types.append(get_translation(ui_lang, "READ.content_type_embeds"))
            if message_to_translate.attachments:
                content_types.append(get_translation(ui_lang, "READ.content_type_attachments"))
            if message_to_translate.stickers:
                content_types.append(get_translation(ui_lang, "READ.content_type_stickers"))
            
            if content_types:
                embed.add_field(
                    name=get_translation(ui_lang, "READ.message_contains_field"),
                    value=", ".join(content_types),
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Check if trying to translate own message
        if message_to_translate.author.id == user_id:
            embed = discord.Embed(
                title=get_translation(ui_lang, "READ.translating_own_message_title"),
                description=get_translation(ui_lang, "READ.translating_own_message_desc"),
                color=0x3498db
            )
            # Continue with translation, just show a friendly notice
        
        # Create/update user in database
        await db.get_or_create_user(user_id, interaction.user.display_name)
        
        # Get user tier and limits
        current_tier = tier_handler.get_user_tier(user_id)
        limits = tier_handler.get_limits(user_id)
        is_premium = current_tier in ['premium', 'pro']
        
        # Check message length against limits
        if len(message_to_translate.content) > limits['text_limit']:
            embed = discord.Embed(
                title=get_translation(ui_lang, "READ.error_text_too_long_title"),
                description=get_translation(ui_lang, "READ.error_text_too_long_desc",
                                          length=len(message_to_translate.content),
                                          tier=current_tier,
                                          limit=limits['text_limit']),
                color=0xFF6B6B
            )
            
            embed.add_field(
                name=get_translation(ui_lang, "READ.upgrade_benefits_field"),
                value=get_translation(ui_lang, "READ.upgrade_benefits_value"),
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Convert language input to code
        target_code = get_language_code(target_lang)
        if target_code == "auto":
            await interaction.response.send_message(
                get_translation(ui_lang, "AUTO.error_auto_not_allowed_for_target"),
                ephemeral=True
            )
            return
        
        # Check channel permissions if in a guild
        if interaction.guild:
            allowed = await db.is_translation_allowed(
                interaction.guild.id,
                interaction.channel.id,
                "text",
                target_code
            )
            if not allowed:
                embed = discord.Embed(
                    title=get_translation(ui_lang, "READ.error_not_allowed_title"),
                    description=get_translation(ui_lang, "READ.error_not_allowed_desc"),
                    color=0xFF6B6B
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        
        # Validate target language
        if not target_code:
            embed = discord.Embed(
                title=get_translation(ui_lang, "READ.error_invalid_target_title"),
                description=get_translation(ui_lang, "READ.error_invalid_target_desc", 
                                          language=target_lang),
                color=0xFF6B6B
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        # Detect the source language
        try:
            source_lang = detect(message_to_translate.content)
            detection_successful = True
        except Exception as e:
            logger.error(f"Language detection error: {e}")
            source_lang = "en"  # Fallback to English
            detection_successful = False
        
        # Don't translate if source and target are the same
        if source_lang == target_code:
            embed = discord.Embed(
                title=get_translation(ui_lang, "READ.same_language_title"),
                description=get_translation(ui_lang, "READ.same_language_desc", 
                                          language=languages.get(target_code, target_code)),
                color=0x3498db
            )
            
            # Still show the message content
            embed.add_field(
                name=get_translation(ui_lang, "READ.message_content_field"),
                value=message_to_translate.content[:1024],
                inline=False
            )
            
            embed.add_field(
                name=get_translation(ui_lang, "READ.message_author_field"),
                value=message_to_translate.author.display_name,
                inline=True
            )
            
            embed.add_field(
                name=get_translation(ui_lang, "READ.message_time_field"),
                value=f"<t:{int(message_to_translate.created_at.timestamp())}:R>",
                inline=True
            )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Create translator and translate
        try:
            translator = GoogleTranslator(source=source_lang, target=target_code)
            translated = translator.translate(message_to_translate.content)
            
            if not translated or translated.strip() == "":
                raise Exception("Translation returned empty result")
                
        except Exception as e:
            logger.error(f"Translation error: {e}")
            embed = discord.Embed(
                title=get_translation(ui_lang, "READ.error_translation_failed_title"),
                description=get_translation(ui_lang, "READ.error_translation_failed_desc", 
                                          error=str(e)),
                color=0xFF6B6B
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return
        
        # Award points based on tier
        points_map = {'free': 1, 'basic': 2, 'premium': 3, 'pro': 4}
        points_awarded = points_map[current_tier]
        reward_db.add_points(user_id, points_awarded, f"Read translation: {source_lang}→{target_code}")
        
        # Track usage and save translation
        await db.track_usage(user_id, text_chars=len(message_to_translate.content))
        await db.save_translation(
            user_id=user_id,
            guild_id=interaction.guild_id or 0,
            original_text=message_to_translate.content,
            translated_text=translated,
            source_lang=source_lang,
            target_lang=target_code,
            translation_type="read"
        )
        
        # Track for achievements
        achievement_db.track_translation(user_id, source_lang, target_code, is_premium)
        new_achievements = achievement_db.check_achievements(user_id)
        if new_achievements:
            await send_achievement_notification(client, user_id, new_achievements)
        
        await safe_track_translation_achievement(
            user_id=user_id,
            username=interaction.user.display_name,
            source_lang=source_lang,
            target_lang=target_code
        )

        uncashed_points, _ = reward_db.get_uncashed_achievement_points(user_id)
        await notify_uncashed_achievements(user_id, interaction.user.display_name, uncashed_points)
        
        # Create and send the translation embeds using the chunked system
        await create_and_send_read_translation_embeds(
            interaction=interaction,
            original_text=message_to_translate.content,
            translated_text=translated,
            source_code=source_lang,
            target_code=target_code,
            tier=current_tier,
            points_awarded=points_awarded,
            limits=limits,
            ui_lang=ui_lang,
            user_id=user_id,
            message_author=message_to_translate.author.display_name,
            message_timestamp=message_to_translate.created_at,
            detection_successful=detection_successful
        )
        
    except Exception as e:
        logger.error(f"Read command error: {e}")
        
        # Get UI language for error message
        try:
            ui_lang = await get_user_ui_language(interaction.user.id)
        except:
            ui_lang = 'en'
        
        error_embed = discord.Embed(
            title=get_translation(ui_lang, "READ.error_general_title"),
            description=get_translation(ui_lang, "READ.error_general_desc", error=str(e)),
            color=0xFF0000
        )
        
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
        else:
            await interaction.followup.send(embed=error_embed, ephemeral=True)


async def create_and_send_read_translation_embeds(
    interaction: discord.Interaction,
    original_text: str,
    translated_text: str,
    source_code: str,
    target_code: str,
    tier: str,
    points_awarded: int,
    limits: dict,
    ui_lang: str,
    user_id: int,
    message_author: str,
    message_timestamp,
    detection_successful: bool
):
    """Create and send read translation embeds with proper truncation and splitting"""
    
    # Get language names and flags
    source_name = get_translation(ui_lang, f"LANGUAGES.{source_code}", default=languages.get(source_code, source_code))
    target_name = get_translation(ui_lang, f"LANGUAGES.{target_code}", default=languages.get(target_code, target_code))
    source_flag = flag_mapping.get(source_code, '🌐')
    target_flag = flag_mapping.get(target_code, '🌐')
    
    # Use the same tier colors as texttr command
    tier_colors = {'free': 0x95a5a6, 'basic': 0x3498db, 'premium': 0xf39c12, 'pro': 0x9b59b6}
    embed_color = tier_colors.get(tier, discord.Color.greyple())
    
    # Calculate footer text
    tier_footers = {
        'free': get_translation(ui_lang, "READ.footer_free", 
                              current=len(original_text), 
                              limit=limits['text_limit']),
        'basic': get_translation(ui_lang, "READ.footer_basic", 
                               current=len(original_text), 
                               limit=limits['text_limit']),
        'premium': get_translation(ui_lang, "READ.footer_premium"),
        'pro': get_translation(ui_lang, "READ.footer_pro")
    }
    
    footer_text = tier_footers[tier]
    if interaction.guild:
        footer_text += " " + get_translation(ui_lang, "READ.footer_server", server=interaction.guild.name)
    else:
        footer_text += " " + get_translation(ui_lang, "READ.footer_dm")
    
    footer_text = footer_text[:2048]  # Discord footer limit
    
    # Field names (truncated to Discord's 256 character limit)
    source_field_name = get_translation(ui_lang, "READ.original_field", 
                                      flag=source_flag, language=source_name)
    if not detection_successful:
        source_field_name += get_translation(ui_lang, "READ.detection_failed_suffix")
    source_field_name = source_field_name[:256]
    
    translation_field_name = get_translation(ui_lang, "READ.translation_field", 
                                           flag=target_flag, language=target_name)[:256]
    points_field_name = get_translation(ui_lang, "READ.points_field")[:256]
    points_field_value = get_translation(ui_lang, "READ.points_value", points=points_awarded)[:1024]
    
    # Helper function to add field and handle embed limits
    def add_field_to_embed(embed_obj, field_name, field_value, field_counter):
        """Helper function to add field and handle embed limits"""
        # Check if current embed can hold another field (Discord limit is 25 fields per embed)
        if field_counter >= 25:
            return None, field_counter  # Signal that we need a new embed
        
        embed_obj.add_field(
            name=field_name,
            value=field_value,
            inline=False
        )
        return embed_obj, field_counter + 1
    
    # Split texts into chunks that fit Discord's 1024 character field limit
    def split_text_for_fields(text, max_length=1020):  # Leave some room for safety
        """Split text into chunks that fit in Discord embed fields"""
        if len(text) <= max_length:
            return [text]
        
        chunks = []
        current_pos = 0
        
        while current_pos < len(text):
            if current_pos + max_length >= len(text):
                # Last chunk
                chunks.append(text[current_pos:])
                break
            
            # Find a good breaking point (prefer word boundaries)
            chunk_end = current_pos + max_length
            
            # Look for word boundary within last 100 characters
            best_break = chunk_end
            for i in range(chunk_end - 100, chunk_end):
                if i > current_pos and text[i] in [' ', '\n', '\t', '.', ',', '!', '?', ';']:
                    best_break = i + 1
                    break
            
            chunks.append(text[current_pos:best_break])
            current_pos = best_break
        
        return chunks
    
    # Create the main embed
    main_embed = discord.Embed(
        title=get_translation(ui_lang, "READ.translation_title")[:256],
        color=embed_color,
        timestamp=datetime.utcnow()
    )
    
    embeds_to_send = [main_embed]
    current_embed = main_embed
    field_count = 0
    
    # Add original text fields (if not hidden)
    if user_id not in hidden_sessions:
        original_chunks = split_text_for_fields(original_text)
        for i, chunk in enumerate(original_chunks):
            field_name = source_field_name if i == 0 else f"{source_field_name} (continued {i+1})"
            
            result, field_count = add_field_to_embed(current_embed, field_name, chunk, field_count)
            if result is None:
                # Need a new embed
                new_embed = discord.Embed(
                    title=f"{get_translation(ui_lang, 'READ.translation_title')} (continued)",
                    color=embed_color
                )
                embeds_to_send.append(new_embed)
                current_embed = new_embed
                field_count = 0
                current_embed.add_field(name=field_name, value=chunk, inline=False)
                field_count += 1
    
    # Add translation fields
    translation_chunks = split_text_for_fields(translated_text)
    for i, chunk in enumerate(translation_chunks):
        field_name = translation_field_name if i == 0 else f"{translation_field_name} (continued {i+1})"
        
        result, field_count = add_field_to_embed(current_embed, field_name, chunk, field_count)
        if result is None:
            # Need a new embed
            new_embed = discord.Embed(
                title=f"{get_translation(ui_lang, 'READ.translation_title')} (continued)",
                color=embed_color
            )
            embeds_to_send.append(new_embed)
            current_embed = new_embed
            field_count = 0
            current_embed.add_field(name=field_name, value=chunk, inline=False)
            field_count += 1
    
    # Only add the metadata fields to the LAST embed to match texttr behavior
    last_embed = embeds_to_send[-1]
    
    # Count fields in the last embed to ensure we don't exceed limits
    last_embed_field_count = len(last_embed.fields)
    
    # Helper to add fields only to the last embed
    def add_metadata_field(embed_obj, field_name, field_value, inline=True):
        nonlocal last_embed_field_count
        if last_embed_field_count >= 25:
            # Create a new embed if we're at the limit
            new_embed = discord.Embed(
                title=f"{get_translation(ui_lang, 'READ.translation_title')} (continued)",
                color=embed_color
            )
            embeds_to_send.append(new_embed)
            new_embed.add_field(name=field_name, value=field_value, inline=inline)
            return new_embed
        else:
            embed_obj.add_field(name=field_name, value=field_value, inline=inline)
            last_embed_field_count += 1
            return embed_obj
    
    # Add metadata fields (author, time, points, usage) to the last embed
    author_field_name = get_translation(ui_lang, "READ.message_author_field")[:256]
    last_embed = add_metadata_field(last_embed, author_field_name, message_author, inline=True)
    
    time_field_name = get_translation(ui_lang, "READ.message_time_field")[:256]
    time_field_value = f"<t:{int(message_timestamp.timestamp())}:R>"
    last_embed = add_metadata_field(last_embed, time_field_name, time_field_value, inline=True)
    
    # Add points field
    last_embed = add_metadata_field(last_embed, points_field_name, points_field_value, inline=True)
    
    # Add character usage for limited tiers
    if tier in ['free', 'basic']:
        usage_field_name = get_translation(ui_lang, "READ.usage_field")[:256]
        usage_field_value = get_translation(ui_lang, "READ.usage_value", 
                                          current=len(original_text), 
                                          limit=limits['text_limit'])[:1024]
        last_embed = add_metadata_field(last_embed, usage_field_name, usage_field_value, inline=True)
    
    # Set footer and timestamp on the final last embed
    embeds_to_send[-1].set_footer(text=footer_text)
    embeds_to_send[-1].timestamp = datetime.utcnow()
    
    # Send all embeds
    await interaction.followup.send(embed=embeds_to_send[0], ephemeral=True)
    
    # Send additional embeds as followups if needed
    for additional_embed in embeds_to_send[1:]:
        await interaction.followup.send(embed=additional_embed, ephemeral=True)


translate_by_id.autocomplete('target_lang')(translated_language_autocomplete)
            
@tree.command(
    name="readimage",
    description="Extract and translate text from an image file"
)
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(
    image="Image attachment to read text from",
    target_lang="Translate extracted text to this language (type to search)"
)
@app_commands.autocomplete(target_lang=translated_language_autocomplete)
async def readimage(
    interaction: discord.Interaction,
    image: discord.Attachment,
    target_lang: str
):
    user_id = interaction.user.id
    ui_lang = await get_user_ui_language(user_id)
    await db.get_or_create_user(user_id, interaction.user.display_name)

    if user_id in tier_handler.pro_users:
        tier = "pro"
    elif user_id in tier_handler.premium_users:
        tier = "premium"
    elif user_id in tier_handler.basic_users:
        tier = "basic"
    else:
        tier = "free"

    max_size_bytes = MEDIA_LIMITS_MB[tier] * 1024 * 1024
    if image.size > max_size_bytes:
        embed = discord.Embed(
            title=get_translation(ui_lang, "MEDIAREAD.error_title"),
            description=get_translation(ui_lang, "MEDIAREAD.error_image_too_large", tier=tier, limit=MEDIA_LIMITS_MB[tier]),
            color=0xE74C3C
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    await interaction.response.defer(ephemeral=True)

    try:
        image_bytes = await image.read()
        pil_image = Image.open(io.BytesIO(image_bytes))

        # Map UI language to Tesseract lang code, fallback to English
        tesseract_lang = tesseract_lang_map.get(ui_lang, "eng")
        extracted_text = pytesseract.image_to_string(pil_image, lang=tesseract_lang)

        if not extracted_text.strip():
            embed = discord.Embed(
                title=get_translation(ui_lang, "MEDIAREAD.error_title"),
                description=get_translation(ui_lang, "MEDIAREAD.error_no_text_found"),
                color=0xE74C3C
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        target_code = get_language_code(target_lang)
        if target_code == "auto":
            await interaction.response.send_message(
                get_translation(ui_lang, "AUTO.error_auto_not_allowed_for_target"),
                ephemeral=True
            )
            return
        if not target_code:
            embed = discord.Embed(
                title=get_translation(ui_lang, "MEDIAREAD.error_title"),
                description=get_translation(ui_lang, "MEDIAREAD.error_invalid_target", language=target_lang),
                color=0xE74C3C
            )
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        translator = GoogleTranslator(source="auto", target=target_code)
        translated_text = translator.translate(extracted_text)

        target_name = get_translation(ui_lang, f"LANGUAGES.{target_code}", default=languages.get(target_code, target_code))
        flag = flag_mapping.get(target_code, "🌐")

        embed = discord.Embed(
            title=get_translation(ui_lang, "MEDIAREAD.title_image"),
            description=get_translation(ui_lang, "MEDIAREAD.description"),
            color=0x2ECC71
        )
        embed.add_field(
            name=get_translation(ui_lang, "MEDIAREAD.original_text"),
            value=extracted_text[:1024],
            inline=False
        )
        embed.add_field(
            name=get_translation(ui_lang, "MEDIAREAD.translated_text", flag=flag, language=target_name),
            value=translated_text[:1024],
            inline=False
        )
        embed.set_footer(text=get_translation(ui_lang, f"MEDIAREAD.footer_{tier}"))

        await interaction.followup.send(embed=embed, ephemeral=True)

    except Exception as e:
        embed = discord.Embed(
            title=get_translation(ui_lang, "MEDIAREAD.error_title"),
            description=get_translation(ui_lang, "MEDIAREAD.error_processing", error=str(e)),
            color=0xE74C3C
        )
        await interaction.followup.send(embed=embed, ephemeral=True)

@tree.context_menu(name="Read Message")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def translate_message_context(interaction: discord.Interaction, message: discord.Message):
    try:
        await track_command_usage(interaction)
        
        user_id = interaction.user.id
        ui_lang = await get_user_ui_language(user_id)
        await db.get_or_create_user(user_id, interaction.user.display_name)
        
        current_tier = tier_handler.get_user_tier(user_id)
        limits = tier_handler.get_limits(user_id)
        is_premium = current_tier in ['premium', 'pro']
        
        if not message.content or not message.content.strip():
            embed = discord.Embed(
                title=get_translation(ui_lang, "CONTEXT.error_no_content_title"),
                description=get_translation(ui_lang, "CONTEXT.error_no_content_desc"),
                color=0xFFA500
            )
            content_types = []
            if message.embeds:
                content_types.append(get_translation(ui_lang, "CONTEXT.content_type_embeds"))
            if message.attachments:
                content_types.append(get_translation(ui_lang, "CONTEXT.content_type_attachments"))
            if message.stickers:
                content_types.append(get_translation(ui_lang, "CONTEXT.content_type_stickers"))
            if message.reactions:
                content_types.append(get_translation(ui_lang, "CONTEXT.content_type_reactions"))
            if content_types:
                embed.add_field(
                    name=get_translation(ui_lang, "CONTEXT.message_contains_field"),
                    value=", ".join(content_types),
                    inline=False
                )
            embed.add_field(
                name=get_translation(ui_lang, "CONTEXT.alternative_field"),
                value=get_translation(ui_lang, "CONTEXT.alternative_value"),
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        if interaction.guild:
            permissions = interaction.channel.permissions_for(interaction.guild.me)
            if not permissions.read_message_history:
                embed = discord.Embed(
                    title=get_translation(ui_lang, "CONTEXT.error_no_permission_title"),
                    description=get_translation(ui_lang, "CONTEXT.error_no_permission_desc"),
                    color=0xFF0000
                )
                embed.add_field(
                    name=get_translation(ui_lang, "CONTEXT.required_permission_field"),
                    value=get_translation(ui_lang, "CONTEXT.required_permission_value"),
                    inline=False
                )
                embed.add_field(
                    name=get_translation(ui_lang, "CONTEXT.fix_permission_field"),
                    value=get_translation(ui_lang, "CONTEXT.fix_permission_value"),
                    inline=False
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
        
        if len(message.content) > limits['text_limit']:
            embed = discord.Embed(
                title=get_translation(ui_lang, "CONTEXT.error_text_too_long_title"),
                description=get_translation(ui_lang, "CONTEXT.error_text_too_long_desc",
                                          length=len(message.content),
                                          tier=current_tier,
                                          limit=limits['text_limit']),
                color=0xFF6B6B
            )
            embed.add_field(
                name=get_translation(ui_lang, "CONTEXT.upgrade_benefits_field"),
                value=get_translation(ui_lang, "CONTEXT.upgrade_benefits_value"),
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        class EnhancedLanguageModal(discord.ui.Modal):
            def __init__(self, message_to_translate, user_tier, user_id, is_premium, ui_language):
                self.message_to_translate = message_to_translate
                self.user_tier = user_tier
                self.user_id = user_id
                self.is_premium = is_premium
                self.ui_lang = ui_language
                
                super().__init__(
                    title=get_translation(ui_language, "CONTEXT.modal_title"),
                    timeout=300.0
                )
                
                self.target_lang = discord.ui.TextInput(
                    label=get_translation(ui_language, "CONTEXT.modal_input_label"),
                    placeholder=get_translation(ui_language, "CONTEXT.modal_input_placeholder"),
                    max_length=50,
                    required=True
                )
                self.add_item(self.target_lang)
            
            async def on_submit(self, modal_interaction: discord.Interaction):
                target_lang_input = self.target_lang.value.strip()
                target_code = get_language_code(target_lang_input)
                
                if not target_code:
                    # Warning embed for invalid language input
                    warning_embed = discord.Embed(
                        title=get_translation(self.ui_lang, "CONTEXT.warning_title"),
                        description=(
                            get_translation(self.ui_lang, "CONTEXT.warning_desc") + "\n\n" +
                            get_translation(self.ui_lang, "CONTEXT.warning_note_read_command") + "\n\n" +
                            get_translation(self.ui_lang, "CONTEXT.warning_note_only_command")
                        ),
                        color=0xFFA500
                    )
                    warning_embed.add_field(
                        name=get_translation(self.ui_lang, "CONTEXT.warning_use_list_title"),
                        value=get_translation(self.ui_lang, "CONTEXT.warning_use_list_desc"),
                        inline=False
                    )
                    await modal_interaction.response.send_message(embed=warning_embed, ephemeral=True)
                    return
                
                if modal_interaction.guild:
                    allowed = await db.is_translation_allowed(
                        modal_interaction.guild.id,
                        modal_interaction.channel.id,
                        "text",
                        target_code
                    )
                    if not allowed:
                        embed = discord.Embed(
                            title=get_translation(self.ui_lang, "CONTEXT.error_not_allowed_title"),
                            description=get_translation(self.ui_lang, "CONTEXT.error_not_allowed_desc"),
                            color=0xFF6B6B
                        )
                        await modal_interaction.response.send_message(embed=embed, ephemeral=True)
                        return
                
                await modal_interaction.response.defer(ephemeral=True)
                
                # Detect source language
                try:
                    source_lang = detect(self.message_to_translate.content)
                    detection_successful = True
                except Exception:
                    source_lang = "en"
                    detection_successful = False
                
                if source_lang == target_code:
                    embed = discord.Embed(
                        title=get_translation(self.ui_lang, "CONTEXT.same_language_title"),
                        description=get_translation(self.ui_lang, "CONTEXT.same_language_desc", language=languages.get(target_code, target_code)),
                        color=0x3498db
                    )
                    embed.add_field(
                        name=get_translation(self.ui_lang, "CONTEXT.message_content_field"),
                        value=self.message_to_translate.content[:1024],
                        inline=False
                    )
                    embed.add_field(
                        name=get_translation(self.ui_lang, "CONTEXT.message_author_field"),
                        value=self.message_to_translate.author.display_name,
                        inline=True
                    )
                    embed.add_field(
                        name=get_translation(self.ui_lang, "CONTEXT.message_time_field"),
                        value=f"<t:{int(self.message_to_translate.created_at.timestamp())}:R>",
                        inline=True
                    )
                    await modal_interaction.followup.send(embed=embed, ephemeral=True)
                    return
                
                try:
                    translator = GoogleTranslator(source=source_lang, target=target_code)
                    translated = translator.translate(self.message_to_translate.content)
                    if not translated or translated.strip() == "":
                        raise Exception("Translation returned empty")
                except Exception as e:
                    embed = discord.Embed(
                        title=get_translation(self.ui_lang, "CONTEXT.error_translation_failed_title"),
                        description=get_translation(self.ui_lang, "CONTEXT.error_translation_failed_desc", error=str(e)),
                        color=0xFF6B6B
                    )
                    await modal_interaction.followup.send(embed=embed, ephemeral=True)
                    return
                
                points_map = {'free': 1, 'basic': 2, 'premium': 3, 'pro': 4}
                points_awarded = points_map.get(self.user_tier, 1)
                reward_db.add_points(self.user_id, points_awarded, f"Context translation: {source_lang}→{target_code}")
                
                await db.track_usage(self.user_id, text_chars=len(self.message_to_translate.content))
                await db.save_translation(
                    user_id=self.user_id,
                    guild_id=modal_interaction.guild_id or 0,
                    original_text=self.message_to_translate.content,
                    translated_text=translated,
                    source_lang=source_lang,
                    target_lang=target_code,
                    translation_type="context"
                )
                
                achievement_db.track_translation(self.user_id, source_lang, target_code, self.is_premium)
                new_achievements = achievement_db.check_achievements(self.user_id)
                if new_achievements:
                    await send_achievement_notification(client, self.user_id, new_achievements)
                
                await safe_track_translation_achievement(
                    user_id=self.user_id,
                    username=modal_interaction.user.display_name,
                    source_lang=source_lang,
                    target_lang=target_code
                )

                uncashed_points, _ = reward_db.get_uncashed_achievement_points(self.user_id)
                await notify_uncashed_achievements(self.user_id, modal_interaction.user.display_name, uncashed_points)
                
                # Create and send the translation embeds using the chunked system
                await create_and_send_context_translation_embeds(
                    interaction=modal_interaction,
                    original_text=self.message_to_translate.content,
                    translated_text=translated,
                    source_code=source_lang,
                    target_code=target_code,
                    tier=self.user_tier,
                    points_awarded=points_awarded,
                    limits=tier_handler.get_limits(self.user_id),
                    ui_lang=self.ui_lang,
                    user_id=self.user_id,
                    message_author=self.message_to_translate.author.display_name,
                    message_timestamp=self.message_to_translate.created_at,
                    detection_successful=detection_successful
                )
            
            async def on_error(self, modal_interaction: discord.Interaction, error: Exception):
                error_embed = discord.Embed(
                    title=get_translation(self.ui_lang, "CONTEXT.error_modal_title"),
                    description=get_translation(self.ui_lang, "CONTEXT.error_modal_desc"),
                    color=0xFF0000
                )
                error_embed.add_field(
                    name=get_translation(self.ui_lang, "CONTEXT.error_help_field"),
                    value=get_translation(self.ui_lang, "CONTEXT.error_help_value"),
                    inline=False
                )
                try:
                    if not modal_interaction.response.is_done():
                        await modal_interaction.response.send_message(embed=error_embed, ephemeral=True)
                    else:
                        await modal_interaction.followup.send(embed=error_embed, ephemeral=True)
                except:
                    pass
        
        modal = EnhancedLanguageModal(message, current_tier, user_id, is_premium, ui_lang)
        await interaction.response.send_modal(modal)
    
    except discord.Forbidden:
        try:
            ui_lang = await get_user_ui_language(interaction.user.id)
        except:
            ui_lang = 'en'
        embed = discord.Embed(
            title=get_translation(ui_lang, "CONTEXT.error_forbidden_title"),
            description=get_translation(ui_lang, "CONTEXT.error_forbidden_desc"),
            color=0xFF0000
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Context menu error: {e}")
        try:
            ui_lang = await get_user_ui_language(interaction.user.id)
        except:
            ui_lang = 'en'
        error_embed = discord.Embed(
            title=get_translation(ui_lang, "CONTEXT.error_unexpected_title"),
            description=get_translation(ui_lang, "CONTEXT.error_unexpected_desc", error=str(e)),
            color=0xFF0000
        )
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=error_embed, ephemeral=True)


async def create_and_send_context_translation_embeds(
    interaction: discord.Interaction,
    original_text: str,
    translated_text: str,
    source_code: str,
    target_code: str,
    tier: str,
    points_awarded: int,
    limits: dict,
    ui_lang: str,
    user_id: int,
    message_author: str,
    message_timestamp,
    detection_successful: bool
):
    """Create and send context translation embeds with proper truncation and splitting"""
    
    # Get language names and flags
    source_name = get_translation(ui_lang, f"LANGUAGES.{source_code}", default=languages.get(source_code, source_code))
    target_name = get_translation(ui_lang, f"LANGUAGES.{target_code}", default=languages.get(target_code, target_code))
    source_flag = flag_mapping.get(source_code, '🌐')
    target_flag = flag_mapping.get(target_code, '🌐')
    
    # Use the same tier colors as texttr command
    tier_colors = {'free': 0x95a5a6, 'basic': 0x3498db, 'premium': 0xf39c12, 'pro': 0x9b59b6}
    embed_color = tier_colors.get(tier, discord.Color.greyple())
    
    # Calculate footer text
    tier_footers = {
        'free': get_translation(ui_lang, "CONTEXT.footer_free"),
        'basic': get_translation(ui_lang, "CONTEXT.footer_basic"),
        'premium': get_translation(ui_lang, "CONTEXT.footer_premium"),
        'pro': get_translation(ui_lang, "CONTEXT.footer_pro")
    }
    
    if interaction.guild:
        footer_text = get_translation(ui_lang, "CONTEXT.footer_guild", 
                                    tier_footer=tier_footers.get(tier, ""), 
                                    author=message_author)
    else:
        footer_text = get_translation(ui_lang, "CONTEXT.footer_dm", 
                                    tier_footer=tier_footers.get(tier, ""), 
                                    author=message_author)
    
    footer_text = footer_text[:2048]  # Discord footer limit
    
    # Field names (truncated to Discord's 256 character limit)
    source_field_name = get_translation(ui_lang, "CONTEXT.original_field", 
                                      flag=source_flag, language=source_name)
    if not detection_successful:
        source_field_name += get_translation(ui_lang, "CONTEXT.detection_failed_suffix")
    source_field_name = source_field_name[:256]
    
    translation_field_name = get_translation(ui_lang, "CONTEXT.translation_field", 
                                           flag=target_flag, language=target_name)[:256]
    points_field_name = get_translation(ui_lang, "CONTEXT.points_field")[:256]
    points_field_value = get_translation(ui_lang, "CONTEXT.points_value", points=points_awarded)[:1024]
    
    # Helper function to add field and handle embed limits
    def add_field_to_embed(embed_obj, field_name, field_value, field_counter):
        """Helper function to add field and handle embed limits"""
        # Check if current embed can hold another field (Discord limit is 25 fields per embed)
        if field_counter >= 25:
            return None, field_counter  # Signal that we need a new embed
        
        embed_obj.add_field(
            name=field_name,
            value=field_value,
            inline=False
        )
        return embed_obj, field_counter + 1
    
    # Split texts into chunks that fit Discord's 1024 character field limit
    def split_text_for_fields(text, max_length=1020):  # Leave some room for safety
        """Split text into chunks that fit in Discord embed fields"""
        if len(text) <= max_length:
            return [text]
        
        chunks = []
        current_pos = 0
        
        while current_pos < len(text):
            if current_pos + max_length >= len(text):
                # Last chunk
                chunks.append(text[current_pos:])
                break
            
            # Find a good breaking point (prefer word boundaries)
            chunk_end = current_pos + max_length
            
            # Look for word boundary within last 100 characters
            best_break = chunk_end
            for i in range(chunk_end - 100, chunk_end):
                if i > current_pos and text[i] in [' ', '\n', '\t', '.', ',', '!', '?', ';']:
                    best_break = i + 1
                    break
            
            chunks.append(text[current_pos:best_break])
            current_pos = best_break
        
        return chunks
    
    # Create the main embed
    main_embed = discord.Embed(
        title=get_translation(ui_lang, "CONTEXT.translation_title")[:256],
        color=embed_color,
        timestamp=datetime.utcnow()
    )
    
    embeds_to_send = [main_embed]
    current_embed = main_embed
    field_count = 0
    
    # Add original text fields (if not hidden)
    if user_id not in hidden_sessions:
        original_chunks = split_text_for_fields(original_text)
        for i, chunk in enumerate(original_chunks):
            field_name = source_field_name if i == 0 else f"{source_field_name} (continued {i+1})"
            
            result, field_count = add_field_to_embed(current_embed, field_name, chunk, field_count)
            if result is None:
                # Need a new embed
                new_embed = discord.Embed(
                    title=f"{get_translation(ui_lang, 'CONTEXT.translation_title')} (continued)",
                    color=embed_color
                )
                embeds_to_send.append(new_embed)
                current_embed = new_embed
                field_count = 0
                current_embed.add_field(name=field_name, value=chunk, inline=False)
                field_count += 1
    
    # Add translation fields
    translation_chunks = split_text_for_fields(translated_text)
    for i, chunk in enumerate(translation_chunks):
        field_name = translation_field_name if i == 0 else f"{translation_field_name} (continued {i+1})"
        
        result, field_count = add_field_to_embed(current_embed, field_name, chunk, field_count)
        if result is None:
            # Need a new embed
            new_embed = discord.Embed(
                title=f"{get_translation(ui_lang, 'CONTEXT.translation_title')} (continued)",
                color=embed_color
            )
            embeds_to_send.append(new_embed)
            current_embed = new_embed
            field_count = 0
            current_embed.add_field(name=field_name, value=chunk, inline=False)
            field_count += 1
    
    # Only add the metadata fields to the LAST embed to match texttr behavior
    last_embed = embeds_to_send[-1]
    
    # Count fields in the last embed to ensure we don't exceed limits
    last_embed_field_count = len(last_embed.fields)
    
    # Helper to add fields only to the last embed
    def add_metadata_field(embed_obj, field_name, field_value, inline=True):
        nonlocal last_embed_field_count
        if last_embed_field_count >= 25:
            # Create a new embed if we're at the limit
            new_embed = discord.Embed(
                title=f"{get_translation(ui_lang, 'CONTEXT.translation_title')} (continued)",
                color=embed_color
            )
            embeds_to_send.append(new_embed)
            new_embed.add_field(name=field_name, value=field_value, inline=inline)
            return new_embed
        else:
            embed_obj.add_field(name=field_name, value=field_value, inline=inline)
            last_embed_field_count += 1
            return embed_obj
    
    # Add metadata fields (author, time, points, usage) to the last embed
    author_field_name = get_translation(ui_lang, "CONTEXT.message_author_field")[:256]
    last_embed = add_metadata_field(last_embed, author_field_name, message_author, inline=True)
    
    time_field_name = get_translation(ui_lang, "CONTEXT.message_time_field")[:256]
    time_field_value = f"<t:{int(message_timestamp.timestamp())}:R>"
    last_embed = add_metadata_field(last_embed, time_field_name, time_field_value, inline=True)
    
    # Add points field
    last_embed = add_metadata_field(last_embed, points_field_name, points_field_value, inline=True)
    
    # Add character usage for limited tiers
    if tier in ['free', 'basic']:
        usage_field_name = get_translation(ui_lang, "CONTEXT.usage_field")[:256]
        usage_field_value = get_translation(ui_lang, "CONTEXT.usage_value", 
                                          current=len(original_text), 
                                          limit=limits['text_limit'])[:1024]
        last_embed = add_metadata_field(last_embed, usage_field_name, usage_field_value, inline=True)
    
    # Set footer and timestamp on the final last embed
    embeds_to_send[-1].set_footer(text=footer_text)
    embeds_to_send[-1].timestamp = datetime.utcnow()
    
    # Send all embeds
    await interaction.followup.send(embed=embeds_to_send[0], ephemeral=True)
    
    # Send additional embeds as followups if needed
    for additional_embed in embeds_to_send[1:]:
        await interaction.followup.send(embed=additional_embed, ephemeral=True)

class AchievementView(discord.ui.View):
    def __init__(self, user_id: int, ui_lang: str):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.ui_lang = ui_lang

        # Set button labels properly here
        self.add_item(discord.ui.Button(
            label=get_translation(ui_lang, "ACHIEVEMENTS.button_collection"),
            style=discord.ButtonStyle.success,
            custom_id="ach_collection"
        ))
        self.add_item(discord.ui.Button(
            label=get_translation(ui_lang, "ACHIEVEMENTS.button_browse"),
            style=discord.ButtonStyle.primary,
            custom_id="ach_browse"
        ))
        self.add_item(discord.ui.Button(
            label=get_translation(ui_lang, "ACHIEVEMENTS.button_quick_goals"),
            style=discord.ButtonStyle.secondary,
            custom_id="ach_goals"
        ))
        self.add_item(discord.ui.Button(
            label=get_translation(ui_lang, "ACHIEVEMENTS.button_cashout"),
            style=discord.ButtonStyle.success,
            custom_id="ach_cashout"
        ))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

@tree.command(name="achievements", description="View your achievements and progress")
async def achievements_command(interaction: discord.Interaction):
    ui_lang = "en"
    try:
        user_id = interaction.user.id
        username = interaction.user.display_name

        try:
            ui_lang = await get_user_ui_language(user_id)
        except:
            ui_lang = "en"

        # Define your allowed rank ladder matching your JSON keys exactly
        rank_ladder = [
            {"name": "Newcomer", "min_points": 0, "emoji": "", "color": 0x95a5a6},
            {"name": "Explorer", "min_points": 100, "emoji": "", "color": 0x3498db},
            {"name": "Translator", "min_points": 500, "emoji": "", "color": 0x2ecc71},
            {"name": "Linguist", "min_points": 1500, "emoji": "", "color": 0xf39c12},
            {"name": "Polyglot", "min_points": 5000, "emoji": "", "color": 0x9b59b6},
            {"name": "Expert", "min_points": 10000, "emoji": "", "color": 0xf1c40f},
            {"name": "Master", "min_points": 15000, "emoji": "", "color": 0xe74c3c},
            {"name": "Legend", "min_points": 50000, "emoji": "", "color": 0xff6b35},
            {"name": "Max_Level", "min_points": 100000, "emoji": "", "color": 0x1abc9c},
        ]

        ALLOWED_RANK_NAMES = {r["name"] for r in rank_ladder}

        # Function to get current rank from points safely
        def get_rank_from_points(points: int) -> dict:
            rank = None
            for r in sorted(rank_ladder, key=lambda x: x["min_points"], reverse=True):
                if points >= r["min_points"]:
                    rank = r
                    break
            if not rank or rank["name"] not in ALLOWED_RANK_NAMES:
                rank = rank_ladder[0]  # fallback to Newcomer
            return rank

        # Get user data from your DB
        try:
            user_data = reward_db.get_or_create_user(user_id, username)
            activity_points = user_data.get("points", 0)
            total_points = user_data.get("total_earned", 0)
        except:
            activity_points = 0
            total_points = 0

        try:
            uncashed_points, _ = reward_db.get_uncashed_achievement_points(user_id)
            user_achievements = achievement_db.get_user_achievements(user_id) or []
            earned_achievement_ids = [str(ach.get("id", "")) if isinstance(ach, dict) else str(ach) for ach in user_achievements]
        except:
            uncashed_points = 0
            earned_achievement_ids = []

        try:
            total_achievement_points = sum(ACHIEVEMENTS[ach_id].get("points", 0) for ach_id in earned_achievement_ids if ach_id in ACHIEVEMENTS)
            cashed_achievement_points = total_achievement_points - uncashed_points
            total_points_display = total_points + total_achievement_points
        except:
            total_achievement_points = 0
            cashed_achievement_points = 0
            total_points_display = total_points

        rank_info = get_rank_from_points(total_points_display)
        rank_name_raw = rank_info["name"]
        rank_color = rank_info["color"]
        rank_emoji = rank_info["emoji"]

        # Translate rank name using your JSON keys, fallback if missing
        rank_name = get_translation(ui_lang, f"RANKS.{rank_name_raw}", default=f"{rank_emoji} {rank_name_raw}")

        # Calculate next rank info
        next_rank = None
        for r in sorted(rank_ladder, key=lambda x: x["min_points"]):
            if r["min_points"] > rank_info["min_points"]:
                next_rank = r
                break

        def create_progress_bar(current, target, length=12):
            if target == 0:
                return f"🌟{'▓'*length}🌟 " + get_translation(ui_lang, "ACHIEVEMENTS.progress_bar_max", default="MAX")
            progress = min(current / target, 1.0)
            filled = int(progress * length)
            empty = length - filled
            percentage = int(progress * 100)
            if percentage == 100:
                return f"🌟{'▓'*length}🌟 " + get_translation(ui_lang, "ACHIEVEMENTS.progress_bar_complete", default="Complete")
            elif percentage >= 75:
                style = "🔥"
            elif percentage >= 50:
                style = "⚡"
            elif percentage >= 25:
                style = "💫"
            else:
                style = "✨"
            return f"{style}{'▓'*filled}{'░'*empty}{style} {percentage}%"

        # Prepare rank progress display
        if next_rank:
            points_needed = next_rank["min_points"] - total_points_display
            rank_progress = create_progress_bar(total_points_display - rank_info["min_points"], points_needed)
            next_rank_name = get_translation(ui_lang, f"RANKS.{next_rank['name']}", default=next_rank["name"])
        else:
            points_needed = 0
            rank_progress = create_progress_bar(1, 1)  # full bar
            next_rank_name = get_translation(ui_lang, "RANKS.Max_Level", default="Max Level")

        completion_rate = (len(earned_achievement_ids) / len(ACHIEVEMENTS)) * 100 if ACHIEVEMENTS else 0

        format_params = {
            "username": username,
            "rank_emoji": rank_emoji,
            "rank_name": rank_name,
            "total_points": total_points_display,
            "completion_bar": create_progress_bar(len(earned_achievement_ids), len(ACHIEVEMENTS)),
            "earned_count": len(earned_achievement_ids),
            "total_achievements": len(ACHIEVEMENTS),
            "completion_rate": completion_rate,
            "activity_points": activity_points,
            "cashed_achievement_points": cashed_achievement_points,
            "uncashed_points": uncashed_points,
            "next_rank_name": next_rank_name,
            "points_needed": points_needed,
            "rank_progress": rank_progress
        }

        embed = discord.Embed(
            title=get_translation(ui_lang, "ACHIEVEMENTS.dashboard_title").format(**format_params),
            description=get_translation(ui_lang, "ACHIEVEMENTS.dashboard_description").format(**format_params),
            color=rank_color
        )

        embed.add_field(
            name=get_translation(ui_lang, "ACHIEVEMENTS.completion_title"),
            value=get_translation(ui_lang, "ACHIEVEMENTS.completion_value").format(**format_params),
            inline=False
        )

        embed.add_field(
            name=get_translation(ui_lang, "ACHIEVEMENTS.points_breakdown_title"),
            value=get_translation(ui_lang, "ACHIEVEMENTS.points_breakdown_value").format(**format_params),
            inline=True
        )

        if uncashed_points > 0:
            embed.add_field(
                name=get_translation(ui_lang, "ACHIEVEMENTS.cashout_available_title"),
                value=get_translation(ui_lang, "ACHIEVEMENTS.cashout_available_value").format(**format_params),
                inline=True
            )
        else:
            embed.add_field(
                name=get_translation(ui_lang, "ACHIEVEMENTS.all_cashed_title"),
                value=get_translation(ui_lang, "ACHIEVEMENTS.all_cashed_value"),
                inline=True
            )

        recent_achievements = earned_achievement_ids[-3:] if earned_achievement_ids else []
        if recent_achievements:
            recent_text = ""
            for ach_id in reversed(recent_achievements):
                ach_data = ACHIEVEMENTS.get(ach_id, {})
                rarity_key = ach_data.get("rarity", "Common")
                rarity_display = get_translation(ui_lang, f"RARITIES.{rarity_key}", default=rarity_key)
                name = get_translation(ui_lang, f"ACHIEVEMENTS.names.{ach_id}", default=ach_id)
                style = {"Common": "✨", "Uncommon": "🌟", "Rare": "💎", "Epic": "🔮", "Legendary": "👑"}.get(rarity_key, "✨")
                recent_text += f"{style} **{name}**\n"
            embed.add_field(
                name=get_translation(ui_lang, "ACHIEVEMENTS.recent_achievements_title"),
                value=recent_text,
                inline=False
            )
        else:
            embed.add_field(
                name=get_translation(ui_lang, "ACHIEVEMENTS.get_started_title"),
                value=get_translation(ui_lang, "ACHIEVEMENTS.get_started_value"),
                inline=False
            )

        if next_rank:
            embed.add_field(
                name=get_translation(ui_lang, "ACHIEVEMENTS.next_rank_title"),
                value=get_translation(ui_lang, "RANKS.next_rank").format(next_rank=next_rank_name, points_needed=points_needed),
                inline=False
            )

    
        view = AchievementView(user_id=user_id, ui_lang=ui_lang)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    except Exception as e:
        logger.error(f"/achievements error: {e}")
        try:
            ui_lang = await get_user_ui_language(interaction.user.id)
        except:
            ui_lang = "en"

        embed = discord.Embed(
            title=get_translation(ui_lang, "ACHIEVEMENTS.error_title"),
            description=get_translation(ui_lang, "ACHIEVEMENTS.error_description"),
            color=0xe74c3c
        )
        embed.add_field(
            name=get_translation(ui_lang, "ACHIEVEMENTS.error_what_to_try"),
            value=get_translation(ui_lang, "ACHIEVEMENTS.error_try_steps"),
            inline=False
        )
        embed.add_field(
            name=get_translation(ui_lang, "ACHIEVEMENTS.error_need_help"),
            value=get_translation(ui_lang, "ACHIEVEMENTS.error_support_server"),
            inline=False
        )
        embed.set_footer(text=get_translation(ui_lang, "ACHIEVEMENTS.error_footer"))

        # Only respond if not responded yet (to avoid InteractionResponded error)
        if not interaction.response.is_done():
            await interaction.response.send_message(embed=embed, ephemeral=True)
        else:
            await interaction.followup.send(embed=embed, ephemeral=True)
class AchievementsPaginator(View):
    def __init__(self, embeds: list[discord.Embed], user_id: int, current_page: int = 0):
        super().__init__(timeout=60)
        self.embeds = embeds
        self.index = current_page
        self.user_id = user_id
        self.update_buttons()

    def update_buttons(self):
        self.clear_items()
        if self.index > 0:
            self.add_item(Button(label='⬅️', custom_id=f'ach_browse:{self.index - 1}', style=discord.ButtonStyle.secondary))
        if self.index < len(self.embeds) - 1:
            self.add_item(Button(label='➡️', custom_id=f'ach_browse:{self.index + 1}', style=discord.ButtonStyle.secondary))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

@client.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type != discord.InteractionType.component:
        return

    user_id = interaction.user.id
    ui_lang = await get_user_ui_language(user_id)
    username = interaction.user.display_name
    custom_id = interaction.data.get("custom_id")

    user_achievements = achievement_db.get_user_achievements(user_id) or []
    earned_achievement_ids = [
        str(ach.get("id", "") if isinstance(ach, dict) else ach)
        for ach in user_achievements
    ]
    uncashed_points, uncashed_achievements = reward_db.get_uncashed_achievement_points(user_id)

    if custom_id == "ach_cashout":
        if uncashed_points > 0:
            converted = reward_db.cash_out_achievements(user_id)
            embed = discord.Embed(
                title=get_translation(ui_lang, "ACHIEVEMENTS.quick_cashout_success_title"),
                description=get_translation(ui_lang, "ACHIEVEMENTS.quick_cashout_success_desc").format(converted_points=converted),
                color=0x2ecc71
            )
            embed.set_footer(text=get_translation(ui_lang, "ACHIEVEMENTS.conversion_complete_title"))
        else:
            embed = discord.Embed(
                title=get_translation(ui_lang, "ACHIEVEMENTS.no_cashout_title"),
                description=get_translation(ui_lang, "ACHIEVEMENTS.no_cashout_desc"),
                color=0xe74c3c
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    elif custom_id == "ach_goals":
        user_data = reward_db.get_or_create_user(user_id, username)
        translations = user_data.get('total_sessions', 0)

        embed = discord.Embed(
            title=get_translation(ui_lang, "ACHIEVEMENTS.quick_goals_title"),
            description=get_translation(ui_lang, "ACHIEVEMENTS.quick_goals_description"),
            color=0xe67e22
        )

        suggestions = []
        milestones = [1, 5, 10, 25, 50, 100, 250, 500]
        for milestone in milestones:
            if translations < milestone:
                remaining = milestone - translations
                difficulty = "🟢" if remaining <= 5 else "🟡" if remaining <= 25 else "🔴"
                suggestions.append((
                    get_translation(ui_lang, 'ACHIEVEMENTS.milestone_translation').format(milestone=milestone),
                    get_translation(ui_lang, 'ACHIEVEMENTS.milestone_complete_more').format(remaining=remaining) + "\n" + difficulty
                ))
                break

        for ach_id in ["first_voice", "feedback_giver", "auto_translate_user"]:
            if ach_id not in earned_achievement_ids:
                name = get_translation(ui_lang, f"ACHIEVEMENTS.names.{ach_id}")
                desc_key = f"ACHIEVEMENTS.descriptions.{ach_id}"
                desc = get_translation(ui_lang, desc_key, default=ACHIEVEMENTS[ach_id]["description"])
                suggestions.append((
                    name,
                    desc + "\n🟢"
                ))

        for i, (name, desc) in enumerate(suggestions[:5], 1):
            embed.add_field(name=f"{i}. {name}", value=desc, inline=False)

        if suggestions:
            total_potential = 50 * len(suggestions)
            embed.add_field(
                name=get_translation(ui_lang, "ACHIEVEMENTS.potential_earnings_title"),
                value=get_translation(ui_lang, "ACHIEVEMENTS.potential_earnings_value").format(potential_points=total_potential),
                inline=False
            )
        else:
            embed.add_field(
                name=get_translation(ui_lang, "ACHIEVEMENTS.quick_goals_none"),
                value=get_translation(ui_lang, "ACHIEVEMENTS.quick_goals_footer"),
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    elif custom_id == "ach_collection":
        embed = discord.Embed(
            title=get_translation(ui_lang, "ACHIEVEMENTS.collection_title").format(username=username),
            description=get_translation(ui_lang, "ACHIEVEMENTS.collection_description").format(earned_count=len(earned_achievement_ids)),
            color=0xf1c40f
        )

        grouped = {"Legendary": [], "Epic": [], "Rare": [], "Uncommon": [], "Common": []}
        for ach_id in earned_achievement_ids:
            if ach_id in ACHIEVEMENTS:
                ach_data = ACHIEVEMENTS[ach_id]
                rarity = ach_data.get("rarity", "Common")
                grouped[rarity].append(ach_id)

        rarity_order = ["Legendary", "Epic", "Rare", "Uncommon", "Common"]
        rarity_emojis = {
            "Legendary": "👑",
            "Epic": "🔮",
            "Rare": "💎",
            "Uncommon": "🌟",
            "Common": "✨"
        }

        for rarity in rarity_order:
            ids = grouped[rarity]
            if ids:
                emoji = rarity_emojis[rarity]
                value = ""
                for ach_id in ids:
                    name = get_translation(ui_lang, f"ACHIEVEMENTS.names.{ach_id}")
                    status = "💰" if ach_id in uncashed_achievements else "✅"
                    value += f"{status} {emoji} **{name}**\n"
                embed.add_field(name=f"{emoji} {rarity}", value=value, inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    elif custom_id.startswith("ach_browse"):
        page = int(custom_id.split(":")[-1]) if ":" in custom_id else 0
        achievements_list = list(ACHIEVEMENTS.items())
        chunks = [achievements_list[i:i + 25] for i in range(0, len(achievements_list), 25)]

        embed_pages = []
        for chunk in chunks:
            embed = discord.Embed(
                title=get_translation(ui_lang, "ACHIEVEMENTS.browse_title"),
                description=get_translation(ui_lang, "ACHIEVEMENTS.browse_description"),
                color=0x3498db
            )
            for ach_id, data in chunk:
                name = get_translation(ui_lang, f"ACHIEVEMENTS.names.{ach_id}", default=data['name'])
                description = get_translation(ui_lang, f"ACHIEVEMENTS.descriptions.{ach_id}", default=data['description'])
                status = "✅" if ach_id in earned_achievement_ids else "❌"
                embed.add_field(name=f"{status} {name}", value=description, inline=False)
            embed_pages.append(embed)

        view = AchievementsPaginator(embed_pages, user_id, current_page=page)
        await interaction.response.send_message(embed=embed_pages[page], ephemeral=True, view=view)


# Helper functions for the achievement system
def get_next_translation_milestone(current):
    """Get the next translation milestone"""
    milestones = [1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000]
    for milestone in milestones:
        if current < milestone:
            return milestone
    return current + 1000  # If beyond all milestones

def get_next_voice_milestone(current):
    """Get the next voice session milestone"""
    milestones = [1, 5, 10, 25, 50, 100, 250, 500]
    for milestone in milestones:
        if current < milestone:
            return milestone
    return current + 100  # If beyond all milestones

def get_next_language_milestone(current):
    """Get the next language diversity milestone"""
    milestones = [2, 5, 10, 15, 25, 50, 75, 100]
    for milestone in milestones:
        if current < milestone:
            return milestone
    return current + 25  # If beyond all milestones

def get_current_rank_min_points(points):
    """Get the minimum points for the current rank"""
    ranks = [
        {"name": "Newcomer", "min_points": 0},
        {"name": "Explorer", "min_points": 100},
        {"name": "Translator", "min_points": 500},
        {"name": "Linguist", "min_points": 1500},
        {"name": "Polyglot", "min_points": 5000},
        {"name": "Master", "min_points": 15000},
        {"name": "Legend", "min_points": 50000}
    ]
    
    current_rank_min = 0
    for rank in ranks:
        if points >= rank["min_points"]:
            current_rank_min = rank["min_points"]
        else:
            break
    
    return current_rank_min

def get_next_rank_info(points):
    """Get information about the next rank"""
    ranks = [
        {"name": "Explorer", "min_points": 100},
        {"name": "Translator", "min_points": 500},
        {"name": "Linguist", "min_points": 1500},
        {"name": "Polyglot", "min_points": 5000},
        {"name": "Master", "min_points": 15000},
        {"name": "Legend", "min_points": 50000}
    ]
    
    for rank in ranks:
        if points < rank["min_points"]:
            return {
                "name": rank["name"],
                "points_needed": rank["min_points"] - points
            }
    
    return None  # Already at max rank



# Helper functions for the enhanced UI
def get_next_translation_milestone(current_translations):
    """Get the next translation milestone"""
    milestones = [1, 5, 10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000]
    for milestone in milestones:
        if current_translations < milestone:
            return milestone
    return current_translations + 1000  # If beyond all milestones

def get_next_voice_milestone(current_voice):
    """Get the next voice milestone"""
    milestones = [1, 5, 10, 25, 50, 100, 250, 500]
    for milestone in milestones:
        if current_voice < milestone:
            return milestone
    return current_voice + 100

def get_next_language_milestone(current_languages):
    """Get the next language milestone"""
    milestones = [2, 5, 10, 15, 25, 50, 75, 100]
    for milestone in milestones:
        if current_languages < milestone:
            return milestone
    return current_languages + 10

def get_next_rank_info(current_points):
    """Get information about the next rank"""
    ranks = [
        {"name": "Newcomer", "points": 0, "emoji": "🆕"},
        {"name": "Explorer", "points": 100, "emoji": "🗺️"},
        {"name": "Translator", "points": 500, "emoji": "📝"},
        {"name": "Linguist", "points": 1500, "emoji": "🎓"},
        {"name": "Polyglot", "points": 3000, "emoji": "🌍"},
        {"name": "Expert", "points": 6000, "emoji": "⭐"},
        {"name": "Master", "points": 12000, "emoji": "🏆"},
        {"name": "Legend", "points": 25000, "emoji": "👑"}
    ]
    
    for i, rank in enumerate(ranks):
        if current_points < rank["points"]:
            points_needed = rank["points"] - current_points
            return {
                "name": rank["name"],
                "emoji": rank["emoji"],
                "points_needed": points_needed,
                "total_needed": rank["points"]
            }
    
    return None  # Already at highest rank

def get_current_rank_min_points(current_points):
    """Get the minimum points for current rank"""
    ranks = [0, 100, 500, 1500, 3000, 6000, 12000, 25000]
    
    for i in range(len(ranks) - 1, -1, -1):
        if current_points >= ranks[i]:
            return ranks[i]
    
    return 0

def get_rank_from_points(points):
    """Get rank information from points"""
    if points >= 25000:
        return {"name": "Legend", "emoji": "👑", "color": 0xf1c40f}
    elif points >= 12000:
        return {"name": "Master", "emoji": "🏆", "color": 0xe67e22}
    elif points >= 6000:
        return {"name": "Expert", "emoji": "⭐", "color": 0x9b59b6}
    elif points >= 3000:
        return {"name": "Polyglot", "emoji": "🌍", "color": 0x3498db}
    elif points >= 1500:
        return {"name": "Linguist", "emoji": "🎓", "color": 0x2ecc71}
    elif points >= 500:
        return {"name": "Translator", "emoji": "📝", "color": 0x1abc9c}
    elif points >= 100:
        return {"name": "Explorer", "emoji": "🗺️", "color": 0x34495e}
    else:
        return {"name": "Newcomer", "emoji": "🆕", "color": 0x95a5a6}

# Enhanced notification system for achievements
async def send_achievement_notification(user_id: int, username: str, achievement_data: dict):
    """Send an enhanced achievement notification"""
    try:
        user = await client.fetch_user(user_id)
        if not user:
            return
        
        ach_name = achievement_data.get('name', 'Unknown Achievement')
        ach_desc = achievement_data.get('description', 'No description')
        ach_points = achievement_data.get('points', 0)
        ach_rarity = achievement_data.get('rarity', 'Common')
        
        # Get rarity styling
        rarity_styles = {
            "Common": {"color": 0x95a5a6, "emoji": "⚪", "sparkle": "✨"},
            "Uncommon": {"color": 0x2ecc71, "emoji": "🟢", "sparkle": "🌟"},
            "Rare": {"color": 0x3498db, "emoji": "🔵", "sparkle": "💎"},
            "Epic": {"color": 0x9b59b6, "emoji": "🟣", "sparkle": "🔮"},
            "Legendary": {"color": 0xf1c40f, "emoji": "🟡", "sparkle": "👑"}
        }
        
        style = rarity_styles.get(ach_rarity, rarity_styles["Common"])
        
        embed = discord.Embed(
            title="🎉 Achievement Unlocked!",
            description=f"**{style['sparkle']} {ach_name} {style['sparkle']}**",
            color=style['color']
        )
        
        embed.add_field(
            name="📜 Description",
            value=ach_desc,
            inline=False
        )
        
        embed.add_field(
            name="💎 Reward",
            value=f"**+{ach_points}** points",
            inline=True
        )
        
        embed.add_field(
            name="🏅 Rarity",
            value=f"{style['emoji']} **{ach_rarity}**",
            inline=True
        )
        
        # Get user's new total points
        user_data = reward_db.get_or_create_user(user_id, username)
        total_points = user_data.get('points', 0)
        
        embed.add_field(
            name="🌟 Total Points",
            value=f"**{total_points:,}** points",
            inline=True
        )
        
        # Check if this achievement caused a rank up
        old_rank = get_rank_from_points(total_points - ach_points)
        new_rank = get_rank_from_points(total_points)
        
        if old_rank['name'] != new_rank['name']:
            embed.add_field(
                name="🎊 RANK UP!",
                value=f"{old_rank['emoji']} {old_rank['name']} → {new_rank['emoji']} **{new_rank['name']}**",
                inline=False
            )
        
        embed.set_footer(text="🎮 Use /achievements to view your complete collection!")
        
        await user.send(embed=embed)
        
    except discord.Forbidden:
        # User has DMs disabled
        logger.info(f"Could not send achievement notification to {username} - DMs disabled")
    except Exception as e:
        logger.error(f"Error sending achievement notification: {e}")

# Add this enhanced achievement awarding function
async def award_achievement_enhanced(user_id: int, username: str, achievement_id: str):
    """Award an achievement with enhanced notifications"""
    try:
        if achievement_id not in ACHIEVEMENTS:
            logger.error(f"Unknown achievement ID: {achievement_id}")
            return False
        
        # Check if user already has this achievement
        try:
            user_achievements = achievement_db.get_user_achievements(user_id) if 'achievement_db' in globals() else []
            earned_ids = [str(ach.get('id', '')) if isinstance(ach, dict) else str(ach) for ach in user_achievements]
            
            if achievement_id in earned_ids:
                return False  # Already has this achievement
        except:
            pass
        
        achievement_data = ACHIEVEMENTS[achievement_id]
        points = achievement_data.get('points', 0)
        
        # Award points to user
        reward_db.add_points(user_id, points)
        
        # Save achievement to database
        try:
            if 'achievement_db' in globals():
                achievement_db.award_achievement(user_id, achievement_id)
        except Exception as e:
            logger.error(f"Error saving achievement to database: {e}")
        
        # Send enhanced notification
        await send_achievement_notification(user_id, username, achievement_data)
        
        logger.info(f"🏆 Achievement '{achievement_data.get('name')}' awarded to {username}")
        return True
        
    except Exception as e:
        logger.error(f"Error awarding achievement: {e}")
        return False
@tree.command(name="cashout", description="Convert achievement points to activity points")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def cashout_command(interaction: discord.Interaction):
    try:
        user_id = interaction.user.id
        username = interaction.user.display_name
        ui_lang = await get_user_ui_language(user_id)

        # Get uncashed achievement points
        uncashed_points, uncashed_achievements = reward_db.get_uncashed_achievement_points(user_id)

        if uncashed_points == 0:
            embed = discord.Embed(
                title=get_translation(ui_lang, "CASHOUT.title_empty"),
                description=get_translation(ui_lang, "CASHOUT.desc_empty"),
                color=0xe74c3c
            )

            embed.add_field(
                name=get_translation(ui_lang, "CASHOUT.field_note"),
                value=get_translation(ui_lang, "CASHOUT.field_note_value"),
                inline=False
            )

            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # Cash out the achievements
        converted_points = reward_db.cash_out_achievements(user_id)

        # Get updated user data
        user_data = reward_db.get_or_create_user(user_id, username)
        new_total_points = user_data.get('points', 0)

        embed = discord.Embed(
            title=get_translation(ui_lang, "CASHOUT.title_success"),
            description=get_translation(ui_lang, "CASHOUT.desc_success"),
            color=0x2ecc71
        )

        embed.add_field(
            name=get_translation(ui_lang, "CASHOUT.field_points_added"),
            value=f"**+{converted_points:,}** activity points",
            inline=True
        )

        embed.add_field(
            name=get_translation(ui_lang, "CASHOUT.field_achievements"),
            value=f"**{len(uncashed_achievements)}** achievements",
            inline=True
        )

        embed.add_field(
            name=get_translation(ui_lang, "CASHOUT.field_total"),
            value=f"**{new_total_points:,}** activity points",
            inline=True
        )

        embed.add_field(
            name=get_translation(ui_lang, "CASHOUT.field_status"),
            value=get_translation(ui_lang, "CASHOUT.field_status_note"),
            inline=False
        )

        embed.set_footer(text=get_translation(ui_lang, "CASHOUT.footer"))

        await interaction.response.send_message(embed=embed, ephemeral=True)

        logger.info(f"💰 User {username} ({user_id}) converted {converted_points} points from {len(uncashed_achievements)} achievements")

    except Exception as e:
        logger.error(f"Cashout error: {e}")
        ui_lang = await get_user_ui_language(interaction.user.id)
        await interaction.response.send_message(
            get_translation(ui_lang, "CASHOUT.error_generic"),
            ephemeral=True
        )


# Simplified and safe achievement view
class SafeAchievementView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=300)
        self.user_id = user_id

    @discord.ui.button(label="📋 All Achievements", style=discord.ButtonStyle.primary)
    async def all_achievements(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Get user achievements safely
            user_achievements = []
            unlocked_ids = []
            
            try:
                if 'achievement_db' in globals() and hasattr(achievement_db, 'get_user_achievements'):
                    user_achievements = achievement_db.get_user_achievements(self.user_id) or []
                    unlocked_ids = [str(ach.get('id', '')) if isinstance(ach, dict) else str(ach[0]) for ach in user_achievements]
            except Exception as e:
                logger.error(f"Error getting achievements: {e}")
            
            embed = discord.Embed(
                title="📋 All Achievements",
                description="Complete achievement collection:",
                color=0x3498db
            )
            
            # Define a simple achievement list if ACHIEVEMENTS isn't available
            simple_achievements = [
                ("first_translation", "🌟 First Steps", "Complete your first translation", 10),
                ("translation_5", "📈 Getting Started", "Complete 5 translations", 20),
                ("translation_25", "🎯 Regular User", "Complete 25 translations", 50),
                ("translation_100", "👑 Translation Expert", "Complete 100 translations", 150),
                ("first_voice", "🎤 Voice Debut", "Use voice translation", 15),
                ("voice_5", "🎙️ Voice User", "Use voice translation 5 times", 30),
                ("basic_supporter", "💎 Basic Supporter", "Subscribe to Basic tier", 100),
                ("premium_supporter", "⭐ Premium Supporter", "Subscribe to Premium tier", 200),
                ("pro_supporter", "🚀 Pro Supporter", "Subscribe to Pro tier", 350),
            ]
            
            achievement_text = ""
            
            # Use ACHIEVEMENTS if available, otherwise use simple list
            try:
                if 'ACHIEVEMENTS' in globals() and ACHIEVEMENTS:
                    for ach_id, ach_data in list(ACHIEVEMENTS.items())[:15]:  # Limit to prevent embed overflow
                        status = "✅" if ach_id in unlocked_ids else "❌"
                        name = ach_data.get('name', ach_id)
                        desc = ach_data.get('description', 'No description')
                        points = ach_data.get('points', 25)
                        
                        achievement_text += f"{status} **{name}** ({points} pts)\n    {desc}\n\n"
                else:
                    # Fallback to simple achievements
                    for ach_id, name, desc, points in simple_achievements:
                        status = "✅" if ach_id in unlocked_ids else "❌"
                        achievement_text += f"{status} **{name}** ({points} pts)\n    {desc}\n\n"
            except Exception as e:
                logger.error(f"Error building achievement list: {e}")
                achievement_text = "Error loading achievements. Please try again later."
            
            embed.add_field(
                name="🏆 Available Achievements",
                value=achievement_text or "No achievements available",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"All achievements button error: {e}")
            await interaction.response.send_message("❌ Error loading achievements.", ephemeral=True)

    @discord.ui.button(label="📊 Stats", style=discord.ButtonStyle.secondary)
    async def stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Get user data safely
            user_data = reward_db.get_or_create_user(self.user_id, interaction.user.display_name)
            
            # Get achievement stats safely
            achievement_stats = {}
            try:
                if 'achievement_db' in globals() and hasattr(achievement_db, 'get_user_stats'):
                    achievement_stats = achievement_db.get_user_stats(self.user_id) or {}
            except:
                pass
            
            embed = discord.Embed(
                title="📊 Your Statistics",
                description="Detailed breakdown of your activity:",
                color=0x2ecc71
            )
            
            # Basic stats
            embed.add_field(
                name="💎 Points & Rank",
                value=(
                    f"**{user_data['points']:,}** total points\n"
                    f"**{user_data.get('total_sessions', 0)}** total sessions\n"
                    f"**{len(achievement_stats)}** tracked stats"
                ),
                inline=True
            )
            
            # Translation stats
            embed.add_field(
                name="📝 Translation Activity",
                value=(
                    f"**{achievement_stats.get('total_translations', 0)}** translations completed\n"
                    f"**{achievement_stats.get('unique_languages', 0)}** languages used\n"
                    f"**{achievement_stats.get('voice_sessions', 0)}** voice sessions"
                ),
                inline=True
            )
            
            # Premium status
            is_premium = (self.user_id in tier_handler.premium_users or 
                         self.user_id in tier_handler.basic_users or 
                         self.user_id in tier_handler.pro_users)
            
            tier_name = "Free"
            if self.user_id in tier_handler.pro_users:
                tier_name = "Pro"
            elif self.user_id in tier_handler.premium_users:
                tier_name = "Premium"
            elif self.user_id in tier_handler.basic_users:
                tier_name = "Basic"
            
            embed.add_field(
                name="⭐ Account Status",
                value=(
                    f"**{tier_name}** tier\n"
                    f"Premium: {'Yes' if is_premium else 'No'}\n"
                    f"Member since: Recently"
                ),
                inline=True
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Stats button error: {e}")
            await interaction.response.send_message("❌ Error loading stats.", ephemeral=True)

    @discord.ui.button(label="🏆 Leaderboard", style=discord.ButtonStyle.success)
    async def leaderboard(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Get top users from reward database
            top_users = reward_db.get_leaderboard(limit=10)
            
            embed = discord.Embed(
                title="🏆 Achievement Leaderboard",
                description="Top users by achievement points:",
                color=0xf1c40f
            )
            
            if not top_users:
                embed.description = "No leaderboard data available yet. Be the first to earn points!"
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            leaderboard_text = ""
            for i, user_data in enumerate(top_users, 1):
                user_id = user_data['user_id']
                points = user_data['points']
                sessions = user_data.get('total_sessions', 0)
                
                try:
                    user = await client.fetch_user(user_id)
                    username = user.display_name if user else f"User {user_id}"
                except:
                    username = f"User {user_id}"
                
                # Get rank info safely
                try:
                    rank_info = get_rank_from_points(points)
                    rank_emoji = rank_info.get('emoji', '🆕')
                    rank_name = rank_info.get('name', 'Newcomer')
                except:
                    rank_emoji = '🆕'
                    rank_name = 'Newcomer'
                
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"#{i}"
                
                leaderboard_text += f"{medal} **{username}**\n"
                leaderboard_text += f"    {rank_emoji} {rank_name} • {points:,} pts • {sessions} sessions\n\n"
            
            embed.description = leaderboard_text
            
            # Add user's position if not in top 10
            try:
                user_position = reward_db.get_user_rank(self.user_id)
                if user_position and user_position > 10:
                    user_data = reward_db.get_or_create_user(self.user_id, interaction.user.display_name)
                    embed.add_field(
                        name="📍 Your Position",
                        value=f"#{user_position} - {user_data['points']:,} points",
                        inline=False
                    )
            except Exception as e:
                logger.error(f"Error getting user position: {e}")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Leaderboard error: {e}")
            await interaction.response.send_message("❌ Error loading leaderboard.", ephemeral=True)

    async def on_timeout(self):
        # Disable all buttons when the view times out
        for item in self.children:
            item.disabled = True


# Safe achievement tracking functions
async def safe_track_translation_achievement(user_id: int, username: str, source_lang: str = None, target_lang: str = None):
    """Safely track translation for achievements - FIXED"""
    try:
        # Track in achievement system if available
        if 'achievement_db' in globals() and hasattr(achievement_db, 'track_translation'):
            is_premium = (user_id in tier_handler.premium_users or 
                         user_id in tier_handler.basic_users or 
                         user_id in tier_handler.pro_users)
            achievement_db.track_translation(user_id, source_lang or 'auto', target_lang or 'en', is_premium)
        
        # Only ensure user exists, do NOT add points here!
        try:
            reward_db.get_or_create_user(user_id, username)
            # reward_db.add_points(user_id, 5, "Translation completed")  # <-- REMOVE THIS LINE
        except Exception as e:
            logger.debug(f"Reward tracking failed (non-critical): {e}")
        
        # Check for new achievements
        await safe_check_and_award_achievements(user_id, username, 'translation')
        
    except Exception as e:
        logger.error(f"Error tracking translation achievement: {e}")


async def safe_track_voice_achievement(user_id: int, username: str):
    """Safely track voice usage for achievements - FIXED"""
    try:
        # Track in achievement system if available
        if 'achievement_db' in globals() and hasattr(achievement_db, 'track_voice_session'):
            is_premium = (user_id in tier_handler.premium_users or 
                         user_id in tier_handler.basic_users or 
                         user_id in tier_handler.pro_users)
            achievement_db.track_voice_session(user_id, is_premium)
        
        # FIXED: Use correct reward_db methods
        try:
            # Just create user and add points - don't use add_session
            reward_db.get_or_create_user(user_id, username)
            reward_db.add_points(user_id, 10, "Voice session completed")
        except Exception as e:
            logger.debug(f"Reward tracking failed (non-critical): {e}")
        
        # Check for new achievements
        await safe_check_and_award_achievements(user_id, username, 'voice')
        
    except Exception as e:
        logger.error(f"Error tracking voice achievement: {e}")

async def safe_check_and_award_achievements(user_id: int, username: str, action_type: str = None):
    """Safely check for new achievements and send a generic notification if the count increases, including rank up."""
    try:
        # Get points and rank BEFORE awarding achievements
        try:
            user_data = reward_db.get_or_create_user(user_id, username)
            old_points = user_data.get('points', 0)
            old_rank_info = get_rank_from_points(old_points)
            old_rank = old_rank_info.get('name', 'Newcomer')
        except Exception:
            old_points = 0
            old_rank = 'Newcomer'

        # Get current achievements count and stats before check
        try:
            user_achievements = achievement_db.get_user_achievements(user_id) or []
            prev_count = len(user_achievements)
        except Exception:
            user_achievements = []
            prev_count = 0

        # Get stats (this is your user stats dict)
        try:
            stats = achievement_db.get_user_stats(user_id) or {}
        except Exception:
            stats = {}

        # Fallback to reward system if no stats
        if not stats:
            user_data = reward_db.get_or_create_user(user_id, username)
            stats = {
                'total_translations': user_data.get('total_sessions', 0),
                'voice_sessions': 0,
                'unique_languages': 0,
                'is_premium': (user_id in tier_handler.premium_users or
                               user_id in tier_handler.basic_users or
                               user_id in tier_handler.pro_users),
                'is_early_user': False
            }

        # Dynamically check all achievements from ACHIEVEMENTS
        new_achievements = []
        try:
            for ach_id, ach_data in ACHIEVEMENTS.items():
                if ach_id in [str(ach.get('id', '')) if isinstance(ach, dict) else str(ach[0]) for ach in user_achievements]:
                    continue
                stat_type = ach_data.get('stat', '')
                requirement = ach_data.get('requirement', 0)
                earned = False
                if stat_type == 'translations':
                    earned = stats.get('total_translations', 0) >= requirement
                elif stat_type == 'voice_sessions':
                    earned = stats.get('voice_sessions', 0) >= requirement
                elif stat_type == 'unique_languages':
                    earned = stats.get('unique_languages', 0) >= requirement
                elif stat_type == 'premium':
                    earned = stats.get('is_premium', False)
                elif stat_type == 'early_user':
                    earned = stats.get('is_early_user', False)
                elif stat_type == 'auto_translate_used':
                    earned = stats.get('auto_translate_used', 0) >= requirement
                elif stat_type == 'dm_translations':
                    earned = stats.get('dm_translations', 0) >= requirement
                elif stat_type == 'context_menu_used':
                    earned = stats.get('context_menu_used', 0) >= requirement
                elif stat_type == 'tier_basic':
                    earned = stats.get('is_basic', False)
                elif stat_type == 'tier_premium':
                    earned = stats.get('is_premium', False)
                elif stat_type == 'tier_pro':
                    earned = stats.get('is_pro', False)
                elif stat_type == 'days_subscribed':
                    earned = stats.get('days_subscribed', 0) >= requirement
                elif stat_type == 'point_purchases':
                    earned = stats.get('point_purchases', 0) >= requirement
                elif stat_type == 'total_donated':
                    earned = stats.get('total_donated', 0) >= requirement
                elif stat_type == 'active_days':
                    earned = stats.get('active_days', 0) >= requirement
                elif stat_type == 'feedback_given':
                    earned = stats.get('feedback_given', 0) >= requirement
                elif stat_type == 'servers_invited':
                    earned = stats.get('servers_invited', 0) >= requirement
                elif stat_type == 'total_achievement_points':
                    earned = stats.get('total_achievement_points', 0) >= requirement
                elif stat_type == 'achievements_unlocked':
                    earned = stats.get('achievements_unlocked', 0) >= requirement
                # Add more stat types as needed

                if earned:
                    logger.info(f"🏆 Awarding achievement to {username}: {ach_data.get('name', ach_id)}")
                    try:
                        if 'achievement_db' in globals() and hasattr(achievement_db, 'award_achievement'):
                            achievement_db.award_achievement(user_id, ach_id, ach_data.get('points', 0))
                    except Exception as e:
                        logger.error(f"Error saving achievement to database: {e}")

                    # Do NOT add points here! Points are only added on /cashout
                    new_achievements.append((ach_id, ach_data))
        except Exception as e:
            logger.error(f"Error checking ACHIEVEMENTS: {e}")

        # Get updated achievements count after check
        try:
            user_achievements = achievement_db.get_user_achievements(user_id) or []
            new_count = len(user_achievements)
        except Exception:
            new_count = prev_count

        # Get updated points and rank after check
        try:
            user_data = reward_db.get_or_create_user(user_id, username)
            new_points = user_data.get('points', 0)
            new_rank_info = get_rank_from_points(new_points)
            new_rank = new_rank_info.get('name', 'Newcomer')
        except Exception:
            new_points = old_points
            new_rank = old_rank
    except Exception as e:
        logger.error(f"Error checking achievements for user {user_id}: {e}")
        return []

async def safe_send_achievement_notifications(user_id: int, achievements: list):
    """Safely send achievement unlock notifications"""
    try:
        user = await client.fetch_user(user_id)
        if not user:
            return
        
        for ach_id, ach_data in achievements:
            # Get rarity info safely
            rarity = ach_data.get('rarity', 'Common')
            rarity_info = {'color': 0x95a5a6, 'emoji': '⚪'}
            
            try:
                if 'RARITY_INFO' in globals() and rarity in RARITY_INFO:
                    rarity_info = RARITY_INFO[rarity]
            except:
                pass
            
            embed = discord.Embed(
                title="🎉 Achievement Unlocked!",
                description=f"{rarity_info.get('emoji', '⚪')} **{ach_data.get('name', 'Unknown Achievement')}**\n\n*{ach_data.get('description', 'Achievement completed!')}*",
                color=rarity_info.get('color', 0x95a5a6)
            )
            
            embed.add_field(
                name="💎 Reward",
                value=f"+{ach_data.get('points', 25)} points",
                inline=True
            )
            
            embed.add_field(
                name="🏅 Rarity",
                value=f"{rarity_info.get('emoji', '⚪')} {rarity}",
                inline=True
            )
            
            embed.set_footer(text="Use /achievements to see all your progress!")
            embed.timestamp = discord.utils.utcnow()
            
            try:
                await user.send(embed=embed)
            except discord.Forbidden:
                # User has DMs disabled, skip notification
                pass
            except Exception as e:
                logger.error(f"Error sending achievement notification: {e}")
                
    except Exception as e:
        logger.error(f"Error sending achievement notifications: {e}")

# FIND and REPLACE this problematic function:
def get_rank_from_points(points: int, ui_lang: str) -> dict:
    """Get the translated rank info based on achievement points."""
    ranks = [
        (5000, {'name': 'Grandmaster', 'emoji': '💎', 'color': 0x1abc9c, 'next_rank': 'Max_Level', 'next_points': 0}),
        (2000, {'name': 'Legend', 'emoji': '🏆', 'color': 0xe74c3c, 'next_rank': 'Grandmaster', 'next_points': 5000}),
        (1000, {'name': 'Master', 'emoji': '👑', 'color': 0xe67e22, 'next_rank': 'Legend', 'next_points': 2000}),
        (500,  {'name': 'Expert', 'emoji': '⭐', 'color': 0xf1c40f, 'next_rank': 'Master', 'next_points': 1000}),
        (300,  {'name': 'Dedicated', 'emoji': '🎯', 'color': 0x9b59b6, 'next_rank': 'Expert', 'next_points': 500}),
        (150,  {'name': 'Learner', 'emoji': '📈', 'color': 0x3498db, 'next_rank': 'Dedicated', 'next_points': 300}),
        (50,   {'name': 'Beginner', 'emoji': '🌱', 'color': 0x2ecc71, 'next_rank': 'Learner', 'next_points': 150}),
        (0,    {'name': 'Newcomer', 'emoji': '🆕', 'color': 0x95a5a6, 'next_rank': 'Beginner', 'next_points': 50})
    ]

    try:
        for threshold, rank_info in ranks:
            if points >= threshold:
                result = rank_info.copy()

                # Translate rank name
                rank_key = f"RANKS.{result['name']}"
                result['translated_name'] = get_translation(ui_lang, rank_key, default=f"{result['emoji']} {result['name']}")

                # Next rank info
                next_key = f"RANKS.{result['next_rank']}"
                next_rank_translated = get_translation(ui_lang, next_key, default=f"{result['emoji']} {result['next_rank']}")

                if result['next_points'] > 0:
                    points_needed = result['next_points'] - points
                else:
                    points_needed = 0

                result['points_needed'] = points_needed
                result['next_rank_translated'] = get_translation(
                    ui_lang,
                    "RANKS.next_rank",
                    default=f"Next Rank: {result['next_rank']} (need {points_needed} pts)"
                ).format(next_rank=next_rank_translated, points_needed=points_needed)

                return result

        # Fallback to lowest rank
        result = ranks[-1][1].copy()
        result['points_needed'] = max(50 - points, 0)
        result['translated_name'] = get_translation(ui_lang, "RANKS.Newcomer", default="🆕 Newcomer")
        result['next_rank_translated'] = get_translation(
            ui_lang,
            "RANKS.next_rank",
            default="Next Rank: {next_rank} (need {points_needed} pts)"
        ).format(
            next_rank=get_translation(ui_lang, "RANKS.Beginner", default="🌱 Beginner"),
            points_needed=result['points_needed']
        )
        return result

    except Exception as e:
        return {
            'name': 'Newcomer',
            'emoji': '🆕',
            'color': 0x95a5a6,
            'points_needed': max(50 - points, 0),
            'translated_name': get_translation(ui_lang, "RANKS.Newcomer", default="🆕 Newcomer"),
            'next_rank_translated': get_translation(
                ui_lang,
                "RANKS.next_rank",
                default="Next Rank: {next_rank} (need {points_needed} pts)"
            ).format(
                next_rank=get_translation(ui_lang, "RANKS.Beginner", default="🌱 Beginner"),
                points_needed=max(50 - points, 0)
            )
        }

async def notify_achievement_earned(user_id: int, achievement_data: dict):
    """Send DM notification when achievement is earned"""
    try:
        user = await client.fetch_user(user_id)
        if not user:
            logger.info(f"Could not fetch user {user_id} for achievement notification")
            return
        
        # Extract achievement info safely
        ach_name = achievement_data.get('name', 'Unknown Achievement')
        ach_desc = achievement_data.get('description', 'Achievement unlocked!')
        ach_points = achievement_data.get('points', 25)
        ach_rarity = achievement_data.get('rarity', 'Common')
        
        # Create embed
        embed = discord.Embed(
            title="🎉 Achievement Unlocked!",
            description=f"🏆 **{ach_name}**\n\n*{ach_desc}*",
            color=0xf1c40f
        )
        
        embed.add_field(
            name="💎 Reward",
            value=f"+{ach_points} points",
            inline=True
        )
        
        embed.add_field(
            name="🏅 Rarity",
            value=f"{ach_rarity}",
            inline=True
        )
        
        embed.set_footer(text="Use /achievements to see your progress!")
        embed.timestamp = discord.utils.utcnow()
        
        # Try to send DM
        try:
            await user.send(embed=embed)
            logger.info(f"✅ Achievement notification sent to {user.display_name}: {ach_name}")
        except discord.Forbidden:
            logger.info(f"❌ User {user.display_name} has DMs disabled")
        except Exception as e:
            logger.error(f"Error sending achievement DM: {e}")
            
    except Exception as e:
        logger.error(f"Error in notify_achievement_earned: {e}")

async def notify_uncashed_achievements(user_id: int, username: str, uncashed_points: int):
    """Notify user if they have uncashed achievement points available."""
    try:
        if uncashed_points <= 0:
            return  # Nothing to notify

        user = await client.fetch_user(user_id)
        if not user:
            return

        ui_lang = await get_user_ui_language(user_id)

        embed = discord.Embed(
            title=get_translation(ui_lang, "ACHIEVEMENTS.uncashed_notify_title"),
            description=get_translation(
                ui_lang,
                "ACHIEVEMENTS.uncashed_notify_desc"
            ).format(uncashed_points=f"{uncashed_points:,}"),
            color=0xf1c40f
        )
        embed.set_footer(text=get_translation(ui_lang, "ACHIEVEMENTS.uncashed_notify_footer"))
        await user.send(embed=embed)

    except Exception as e:
        logger.error(f"Error sending uncashed achievement notification: {e}")


async def notify_rank_up(user_id: int, old_rank: str, new_rank: str, total_points: int):
    """Send DM notification when user ranks up"""
    try:
        user = await client.fetch_user(user_id)
        if not user:
            return

        rank_info = get_rank_from_points(total_points)
        rank_name = rank_info.get('name', 'Newcomer')
        rank_emoji = rank_info.get('emoji', '🆕')
        next_rank_name = rank_info.get('next_rank', 'Beginner')
        points_needed = rank_info.get('points_needed', 50)

        # Create embed FIRST
        embed = discord.Embed(
            title="🎊 Rank Up!",
            description=f"{rank_emoji} **Congratulations!**\n\nYou've been promoted from **{old_rank}** to **{new_rank}**!",
            color=rank_info.get('color', 0xf1c40f)
        )

        embed.add_field(
            name="🏅 New Rank",
            value=f"{rank_emoji} {new_rank}",
            inline=True
        )

        embed.add_field(
            name="💎 Total Points",
            value=f"{total_points:,} points",
            inline=True
        )

        # Show progress to next rank
        if next_rank_name != 'Max Level!' and points_needed > 0:
            embed.add_field(
                name="🎯 Next Goal",
                value=f"{next_rank_name} ({points_needed:,} points to go)",
                inline=False
            )
        elif next_rank_name == 'Max Level!':
            embed.add_field(
                name="🏆 Achievement",
                value="You've reached the maximum rank!",
                inline=False
            )

        embed.set_footer(text="Keep translating to reach the next rank!")
        embed.timestamp = discord.utils.utcnow()

        try:
            await user.send(embed=embed)
            logger.info(f"✅ Rank up notification sent to {user.display_name}: {old_rank} → {new_rank}")
        except discord.Forbidden:
            logger.info(f"❌ User {user.display_name} has DMs disabled for rank up")
        except Exception as e:
            logger.error(f"Error sending rank up DM: {e}")

    except Exception as e:
        logger.error(f"Error in notify_rank_up: {e}")

# Add missing database methods to RewardDatabase class
class RewardDatabase:
    # ... existing methods ...
    
    def get_leaderboard(self, limit=10):
        """Get top users by points"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, username, points, total_translations, total_sessions
                FROM users 
                ORDER BY points DESC 
                LIMIT ?
            ''', (limit,))
            
            results = cursor.fetchall()
            conn.close()
            
            return [
                {
                    'user_id': row[0],
                    'username': row[1],
                    'points': row[2],
                    'total_translations': row[3],
                    'total_sessions': row[4]
                }
                for row in results
            ]
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            return []
    
    def get_user_rank(self, user_id: int):
        """Get user's rank position"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) + 1 as rank
                FROM users 
                WHERE points > (SELECT points FROM users WHERE user_id = ?)
            ''', (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            return result[0] if result else None
        except Exception as e:
            logger.error(f"Error getting user rank: {e}")
            return None
    
    def get_user_achievements(self, user_id: int):
        """Get user's unlocked achievements"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('SELECT achievements FROM users WHERE user_id = ?', (user_id,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result and result[0]:
                return json.loads(result[0])
            return []
        except Exception as e:
            logger.error(f"Error getting user achievements: {e}")
            return []
    
    def get_user_badges(self, user_id: int, achievements: list, points: int):
        """Get user's badges based on achievements and points"""
        badges = []
        
        try:
            # Add rank badge
            rank_info = get_rank_from_points(points)
            badges.append({
                'emoji': rank_info['emoji'],
                'title': rank_info['name'],
                'type': 'rank',
                'description': f'Earned with {points} points'
            })
            
            # Add achievement badges
            achievement_badges = {
                'first_translation': {'emoji': '🌟', 'title': 'First Steps', 'type': 'achievement'},
                'translation_100': {'emoji': '👑', 'title': 'Master Translator', 'type': 'achievement'},
                'translation_500': {'emoji': '🏆', 'title': 'Translation Legend', 'type': 'achievement'},
                'languages_15': {'emoji': '🌎', 'title': 'Polyglot', 'type': 'achievement'},
                'languages_30': {'emoji': '🌏', 'title': 'Master Linguist', 'type': 'achievement'},
                'premium_supporter': {'emoji': '⭐', 'title': 'Premium Supporter', 'type': 'special'},
                'early_adopter': {'emoji': '🚀', 'title': 'Pioneer', 'type': 'special'}
            }
            
            for achievement in achievements:
                if achievement in achievement_badges:
                    badges.append(achievement_badges[achievement])
            
            return badges
            
        except Exception as e:
            logger.error(f"Error getting user badges: {e}")
            return badges

@app.route('/webhook/kofi', methods=['POST'])
def handle_kofi_donation():
    try:
        data = request.json
        logger.info(f"Ko-fi webhook received: {data}")
        
        donation_type = data.get('type')
        amount = float(data.get('amount', 0))
        message = data.get('message', '').strip()
        
        # Extract Discord ID from message
        try:
            import re
            id_match = re.search(r'\b(\d{17,19})\b', message)
            if id_match:
                user_id = int(id_match.group(1))
            else:
                user_id = int(message)
        except ValueError:
            logger.error(f"Invalid Discord ID in Ko-fi message: {message}")
            return jsonify({'status': 'error', 'message': 'Invalid Discord ID format'})
        
        # 🚀 PRO TIER: $5+ monthly subscriptions
        if donation_type == 'Subscription' and amount >= 5.00:
            # Calculate pro days based on amount
            if amount >= 60.00:  # Annual pro subscription ($5 x 12)
                pro_days = 365
                tier_name = "Annual Pro"
            elif amount >= 30.00:  # 6-month pro subscription ($5 x 6)
                pro_days = 180
                tier_name = "6-Month Pro"
            elif amount >= 15.00:  # 3-month pro subscription ($5 x 3)
                pro_days = 90
                tier_name = "3-Month Pro"
            else:  # Monthly pro subscription ($5+)
                pro_days = 30
                tier_name = "Monthly Pro"
            
            # Process pro tier in background
            asyncio.run_coroutine_threadsafe(
                process_kofi_pro_tier(user_id, pro_days, data, tier_name),
                client.loop
            )
            
            logger.info(f"Pro subscription processed for user {user_id}: {pro_days} days")
            return jsonify({'status': 'success', 'message': f'Pro subscription activated for {pro_days} days'})
        
        # ⭐ PREMIUM TIER: $3+ monthly subscriptions
        elif donation_type == 'Subscription' and amount >= 3.00:
            # Calculate premium days based on amount
            if amount >= 36.00:  # Annual premium subscription ($3 x 12)
                premium_days = 365
                tier_name = "Annual Premium"
            elif amount >= 18.00:  # 6-month premium subscription ($3 x 6)
                premium_days = 180
                tier_name = "6-Month Premium"
            elif amount >= 9.00:  # 3-month premium subscription ($3 x 3)
                premium_days = 90
                tier_name = "3-Month Premium"
            else:  # Monthly premium subscription ($3+)
                premium_days = 30
                tier_name = "Monthly Premium"
            
            # Process premium tier in background
            asyncio.run_coroutine_threadsafe(
                process_kofi_premium_tier(user_id, premium_days, data, tier_name),
                client.loop
            )
            
            logger.info(f"Premium subscription processed for user {user_id}: {premium_days} days")
            return jsonify({'status': 'success', 'message': f'Premium subscription activated for {premium_days} days'})
        
        # 💎 BASIC TIER: $1+ monthly subscriptions
        elif donation_type == 'Subscription' and amount >= 1.00:
            # Calculate basic days based on amount
            if amount >= 12.00:  # Annual basic subscription ($1 x 12)
                basic_days = 365
                tier_name = "Annual Basic"
            elif amount >= 6.00:  # 6-month basic subscription ($1 x 6)
                basic_days = 180
                tier_name = "6-Month Basic"
            elif amount >= 3.00:  # 3-month basic subscription ($1 x 3)
                basic_days = 90
                tier_name = "3-Month Basic"
            else:  # Monthly basic subscription ($1+)
                basic_days = 30
                tier_name = "Monthly Basic"
            
            # Process basic tier in background
            asyncio.run_coroutine_threadsafe(
                process_kofi_basic_tier(user_id, basic_days, data, tier_name),
                client.loop
            )
            
            logger.info(f"Basic subscription processed for user {user_id}: {basic_days} days")
            return jsonify({'status': 'success', 'message': f'Basic subscription activated for {basic_days} days'})
        
        # 💰 ONE-TIME POINT PURCHASES: One-time donations (no tier upgrade)
        elif donation_type == 'Donation' and amount >= 1.00:
            # Point conversion rates for one-time purchases
            point_packages = {
                1.00: 50,    # $1 = 50 points
                2.00: 110,   # $2 = 110 points (10% bonus)
                3.00: 180,   # $3 = 180 points (20% bonus)
                5.00: 325,   # $5 = 325 points (30% bonus)
                10.00: 700,  # $10 = 700 points (40% bonus)
                20.00: 1500, # $20 = 1500 points (50% bonus)
            }
            
            # Calculate points
            if amount in point_packages:
                points_to_award = point_packages[amount]
            else:
                # Custom amount calculation
                points_to_award = int(amount * 50)  # Base: $1 = 50 points
                
                # Bonus for larger amounts
                if amount >= 20:
                    points_to_award = int(points_to_award * 1.5)  # 50% bonus
                elif amount >= 10:
                    points_to_award = int(points_to_award * 1.4)  # 40% bonus
                elif amount >= 5:
                    points_to_award = int(points_to_award * 1.3)  # 30% bonus
                elif amount >= 3:
                    points_to_award = int(points_to_award * 1.2)  # 20% bonus
                elif amount >= 2:
                    points_to_award = int(points_to_award * 1.1)  # 10% bonus
            
            # Award points only (no tier upgrade)
            safe_db_operation(reward_db.add_points, user_id, points_to_award, f"Ko-fi donation (${amount})")
            
            # Send points notification
            asyncio.run_coroutine_threadsafe(
                send_points_only_notification(user_id, points_to_award, amount),
                client.loop
            )
            
            logger.info(f"Awarded {points_to_award} points to user {user_id} for ${amount} donation (no tier upgrade)")
            return jsonify({'status': 'success', 'message': f'{points_to_award} points awarded'})
        
        # 🆓 FREE TIER: Amounts under $1.00 or invalid types (stays free - $0/month)
        else:
            # Still award small amount of points for any donation attempt
            if donation_type == 'Donation' and 0.50 <= amount < 1.00:
                # Small consolation points for donations under $1
                consolation_points = int(amount * 25)  # $0.50 = 12 points, etc.
                safe_db_operation(reward_db.add_points, user_id, consolation_points, f"Small Ko-fi donation (${amount})")
                
                asyncio.run_coroutine_threadsafe(
                    send_consolation_notification(user_id, consolation_points, amount),
                    client.loop
                )
                
                return jsonify({'status': 'success', 'message': f'{consolation_points} consolation points awarded'})
            else:
                return jsonify({'status': 'ignored', 'message': 'Amount too low or invalid type'})
        
    except Exception as e:
        logger.error(f"Ko-fi webhook error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})    
@app.route('/webhook/topgg', methods=['POST'])
def handle_topgg_vote():
    try:
        auth = request.headers.get('Authorization')
        if auth != "YOUR_TOPGG_WEBHOOK_SECRET":  # Set this to your Top.gg webhook secret
            return jsonify({'error': 'Unauthorized'}), 401

        data = request.json
        user_id = int(data['user'])

        # Award points and achievement
        safe_db_operation(reward_db.add_points, user_id, 50, "Top.gg upvote")
        asyncio.run_coroutine_threadsafe(
            award_achievement_enhanced(user_id, f"User {user_id}", "topgg_voter"),
            client.loop
        )

        # Optionally DM the user
        asyncio.run_coroutine_threadsafe(
            client.fetch_user(user_id).send(
                "🌟 Thank you for upvoting Muse on Top.gg! You've earned 25 points and a special achievement."
            ),
            client.loop
        )

        return jsonify({'status': 'success'})
    except Exception as e:
        logger.error(f"Top.gg vote webhook error: {e}")
        return jsonify({'error': str(e)}), 500
# Updated tier notification function with correct pricing
async def send_tier_notification(user_id: int, tier: str, tier_name: str, kofi_data, expires_at, days: int, emoji: str):
    try:
        user = await client.fetch_user(user_id)
        
        # Tier-specific colors
        colors = {
            "Pro": 0xff6b6b,      # Red for Pro ($5/month)
            "Premium": 0xf1c40f,  # Gold for Premium ($3/month)  
            "Basic": 0x3498db     # Blue for Basic ($1/month)
        }
        
        embed = discord.Embed(
            title=f"{emoji} {tier} Subscription Activated!",
            description=(
                f"Thank you for your **{tier_name}** subscription!\n\n"
                f"**Amount:** ${kofi_data['amount']}\n"
                f"**Duration:** {days} days\n"
                f"**Expires:** {expires_at.strftime('%B %d, %Y')}\n\n"
                f"✨ All {tier.lower()} features are now active!"
            ),
            color=colors.get(tier, 0x95a5a6)
        )
        
        # Tier-specific features with correct pricing
        if tier == "Pro":
            features = (
                "• Unlimited everything\n"
                "• Max 20 translation history\n" 
                "• Priority support\n"
                "• All achievements unlocked! 🏆\n"
                "• **Worth $5/month!**"
            )
        elif tier == "Premium":
            features = (
                "• Extended translation limits\n"
                "• Max 15 translation history\n"
                "• Premium support\n" 
                "• Premium achievements unlocked! 🏆\n"
                "• **Worth $3/month!**"
            )
        else:  # Basic
            features = (
                "• Basic premium features\n"
                "• Max 10 translation history\n"
                "• Basic support\n"
                "• Achievement unlocked! 🏆\n"
                "• **Worth $1/month!**"
            )
        
        embed.add_field(
            name=f"{emoji} {tier} Features Unlocked",
            value=features,
            inline=False
        )
        
        # Add upgrade path
        if tier == "Basic":
            embed.add_field(
                name="🚀 Want More?",
                value="Upgrade to Premium ($3/month) or Pro ($5/month) for even more features!",
                inline=False
            )
        elif tier == "Premium":
            embed.add_field(
                name="🚀 Want Everything?",
                value="Upgrade to Pro ($5/month) for unlimited access to all features!",
                inline=False
            )
        
        embed.add_field(
            name="🎯 What's Next?",
            value="Use `/achievements` to see your new achievements!",
            inline=False
        )
        
        await user.send(embed=embed)
        logger.info(f"✅ Notified user {user_id} about {tier} subscription")
    except Exception as notify_error:
        logger.error(f"⚠️ Couldn't notify user {user_id}: {notify_error}")
# Updated points notification to show correct tier pricing
async def send_points_only_notification(user_id: int, points: int, amount: float):
    try:
        user = await client.fetch_user(user_id)
        if user:
            embed = discord.Embed(
                title="💎 Points Purchased!",
                description=f"Thank you for your ${amount:.2f} donation!",
                color=0x9b59b6
            )
            embed.add_field(
                name="💰 Points Awarded",
                value=f"**{points:,} points** added to your account!",
                inline=False
            )
            embed.add_field(
                name="⭐ Want Subscription Benefits?",
                value=(
                    "**Basic Tier:** $1/month - Basic features\n"
                    "**Premium Tier:** $3/month - Extended features\n"
                    "**Pro Tier:** $5/month - Unlimited everything!"
                ),
                inline=False
            )
            embed.add_field(
                name="🎯 Use Your Points",
                value="Use `/shop` to see what you can buy with points!",
                inline=False
            )
            embed.set_footer(text="💡 Subscriptions unlock features, donations give points!")
            await user.send(embed=embed)
    except Exception as e:
        logger.error(f"Failed to send points notification: {e}")

@tree.command(name="upgrade", description="Get premium access through Ko-fi")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def premium(interaction: discord.Interaction):
    user_id = interaction.user.id
    ui_lang = await get_user_ui_language(user_id)

    embed = discord.Embed(
        title=get_translation(ui_lang, "UPGRADE.title"),
        description=get_translation(ui_lang, "UPGRADE.description"),
        color=0x29abe0
    )

    # Add all tier fields
    embed.add_field(
        name=get_translation(ui_lang, "UPGRADE.free_title"),
        value=get_translation(ui_lang, "UPGRADE.free_value"),
        inline=True
    )

    embed.add_field(
        name=get_translation(ui_lang, "UPGRADE.basic_title"),
        value=get_translation(ui_lang, "UPGRADE.basic_value"),
        inline=True
    )

    embed.add_field(
        name=get_translation(ui_lang, "UPGRADE.premium_title"),
        value=get_translation(ui_lang, "UPGRADE.premium_value"),
        inline=True
    )

    embed.add_field(
        name=get_translation(ui_lang, "UPGRADE.pro_title"),
        value=get_translation(ui_lang, "UPGRADE.pro_value"),
        inline=True
    )

    embed.add_field(
        name=get_translation(ui_lang, "UPGRADE.subscribe_title"),
        value=get_translation(ui_lang, "UPGRADE.subscribe_value", user_id=user_id),
        inline=False
    )

    embed.add_field(
        name=get_translation(ui_lang, "UPGRADE.try_title"),
        value=get_translation(ui_lang, "UPGRADE.try_value"),
        inline=False
    )

    # Add button
    view = discord.ui.View()
    view.add_item(discord.ui.Button(
        label=get_translation(ui_lang, "UPGRADE.button"),
        url="https://ko-fi.com/muse/tiers",
        style=discord.ButtonStyle.link,
        emoji="☕"
    ))

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


@tree.command(name="buypoints", description="Purchase points with one-time Ko-fi donation")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def buy_points(interaction: discord.Interaction):
    user_id = interaction.user.id
    ui_lang = await get_user_ui_language(user_id)

    embed = discord.Embed(
        title=get_translation(ui_lang, "BUYPOINTS.title"),
        description=get_translation(ui_lang, "BUYPOINTS.description"),
        color=0x3498db
    )

    embed.add_field(
        name=get_translation(ui_lang, "BUYPOINTS.packages_title"),
        value=get_translation(ui_lang, "BUYPOINTS.packages_value"),
        inline=False
    )

    embed.add_field(
        name=get_translation(ui_lang, "BUYPOINTS.vs_title"),
        value=get_translation(ui_lang, "BUYPOINTS.vs_value"),
        inline=False
    )

    embed.add_field(
        name=get_translation(ui_lang, "BUYPOINTS.how_title"),
        value=get_translation(ui_lang, "BUYPOINTS.how_value", user_id=user_id),
        inline=False
    )

    view = discord.ui.View()
    view.add_item(discord.ui.Button(
        label=get_translation(ui_lang, "BUYPOINTS.button"),
        url="https://ko-fi.com/yourusername",
        style=discord.ButtonStyle.link
    ))

    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


@tree.command(name="list", description="List all available languages for translation")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def list_languages(interaction: discord.Interaction):
    user_id = interaction.user.id
    ui_lang = await get_user_ui_language(user_id)
    
    embed = discord.Embed(
        title=get_translation(ui_lang, "LIST.title"),
        description=get_translation(ui_lang, "LIST.description"),
        color=discord.Color.blue()
    )
    
    def get_display_language_name(lang_code: str) -> str:
        fallback = languages.get(lang_code, lang_code)
        return get_translation(ui_lang, f"LANGUAGES.{lang_code}", default=fallback)
    
    # Sort based on the translated name
    sorted_languages = sorted(languages.keys(), key=lambda code: get_display_language_name(code).lower())
    
    current_letter = None
    current_field = ""
    field_count = 0
    additional_embeds = []
    current_embed = embed
    
    def add_field_to_embed(embed_obj, field_name, field_value, field_counter):
        """Helper function to add field and handle embed limits"""
        nonlocal current_embed, additional_embeds, field_count
        
        # Check if current embed can hold another field
        if field_counter >= 25:
            # Create new embed
            additional_embed = discord.Embed(
                title=f"{get_translation(ui_lang, 'LIST.title')} (continued)",
                color=discord.Color.blue()
            )
            additional_embeds.append(additional_embed)
            current_embed = additional_embed
            field_counter = 0
        
        # Add the field to current embed
        current_embed.add_field(
            name=field_name,
            value=field_value,
            inline=False
        )
        return field_counter + 1
    
    for code in sorted_languages:
        translated_name = get_display_language_name(code)
        first_letter = translated_name[0].upper()
        
        # Add flag and language entry
        flag = flag_mapping.get(code, '🌐')
        new_entry = f"{flag} `{code}` - {translated_name}\n"
        
        # If we encounter a new letter, finalize the current field
        if first_letter != current_letter:
            if current_field:
                field_count = add_field_to_embed(current_embed, current_letter, current_field.rstrip(), field_count)
            
            current_letter = first_letter
            current_field = new_entry
        else:
            # Check if adding this entry would exceed the 1024 character limit
            if len(current_field + new_entry) > 1024:
                # Finalize current field and start a new one with same letter
                field_count = add_field_to_embed(current_embed, current_letter, current_field.rstrip(), field_count)
                current_field = new_entry
            else:
                current_field += new_entry
    
    # Add the final field
    if current_field:
        field_count = add_field_to_embed(current_embed, current_letter, current_field.rstrip(), field_count)
    
    embed.set_footer(text=get_translation(ui_lang, "LIST.footer"))
    
    # Send the main embed
    await interaction.response.send_message(embed=embed, ephemeral=True)
    
    # Send additional embeds as followups if needed
    for additional_embed in additional_embeds:
        await interaction.followup.send(embed=additional_embed, ephemeral=True)


# Fixed invite command

@tree.command(name="history", description="View your recent translation history")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(limit="Number of translations to show (max 20)")
async def translation_history(interaction: discord.Interaction, limit: int = 10):
    user_id = interaction.user.id
    ui_lang = await get_user_ui_language(user_id)

    def get_display_language_name(lang_code: str) -> str:
        fallback = languages.get(lang_code, lang_code)
        return get_translation(ui_lang, f"LANGUAGES.{lang_code}", default=fallback)

    if user_id in tier_handler.pro_users:
        tier = 'pro'
        limit = min(limit, 20)
    elif user_id in tier_handler.premium_users:
        tier = 'premium'
        limit = min(limit, 15)
    elif user_id in tier_handler.basic_users:
        tier = 'basic'
        limit = min(limit, 10)
    else:
        tier = 'free'
        limit = min(limit, 5)

    history = await db.get_translation_history(user_id, limit)

    if not history:
        embed = discord.Embed(
            title=get_translation(ui_lang, "HISTORY.no_results_title"),
            description=get_translation(ui_lang, "HISTORY.no_results_desc"),
            color=0x95a5a6
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    tier_colors = {'free': 0x95a5a6, 'basic': 0x3498db, 'premium': 0xf39c12, 'pro': 0x9b59b6}

    embed = discord.Embed(
        title=get_translation(ui_lang, "HISTORY.title"),
        description=get_translation(ui_lang, "HISTORY.showing_n", count=len(history)),
        color=tier_colors[tier]
    )

    for i, translation in enumerate(history, 1):
        source_name = get_display_language_name(translation['source_lang'])
        target_name = get_display_language_name(translation['target_lang'])
        source_flag = flag_mapping.get(translation['source_lang'], '🌐')
        target_flag = flag_mapping.get(translation['target_lang'], '🌐')

        original_text = translation['original'][:100] + "..." if len(translation['original']) > 100 else translation['original']
        translated_text = translation['translated'][:100] + "..." if len(translation['translated']) > 100 else translation['translated']

        embed.add_field(
            name=f"{i}. {source_flag} {source_name} → {target_flag} {target_name} ({translation['type']})",
            value=f"**{get_translation(ui_lang, 'HISTORY.original')}** {original_text}\n**{get_translation(ui_lang, 'HISTORY.translated')}** {translated_text}",
            inline=False
        )

    tier_footers = {
        'free': get_translation(ui_lang, "HISTORY.footer_free"),
        'basic': get_translation(ui_lang, "HISTORY.footer_basic"),
        'premium': get_translation(ui_lang, "HISTORY.footer_premium"),
        'pro': get_translation(ui_lang, "HISTORY.footer_pro")
    }

    embed.set_footer(text=tier_footers[tier])
    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="preferences", description="Set your interface language")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(
    ui_language="Language used for bot messages (e.g. en, es)"
)
async def set_preferences(
    interaction: discord.Interaction,
    ui_language: str = None
):
    user_id = interaction.user.id
    current_ui_lang = await get_user_ui_language(user_id)

    def get_display_language_name(lang_code: str, ui_lang: str) -> str:
        fallback = languages.get(lang_code, lang_code)
        return get_translation(ui_lang, f"LANGUAGES.{lang_code}", default=fallback)

    try:
        if not ui_language:
            await interaction.response.send_message(
                get_translation(current_ui_lang, "PREFERENCES.nothing_set"),
                ephemeral=True
            )
            return

        ui_code = get_language_code(ui_language)
        if not ui_code or ui_code not in SUPPORTED_UI_LANGUAGES:
            supported_langs = ", ".join(SUPPORTED_UI_LANGUAGES)
            await interaction.response.send_message(
                get_translation(current_ui_lang, "ERRORS.invalid_ui",
                                language=ui_language, supported=supported_langs),
                ephemeral=True
            )
            return

        await db.update_user_ui_language(user_id, ui_code)

        display = get_display_language_name(ui_code, ui_code)
        flag = flag_mapping.get(ui_code, '🌐')
        label = get_translation(ui_code, 'PREFERENCES.ui_label')

        embed = discord.Embed(
            title=get_translation(ui_code, "PREFERENCES.updated_title"),
            description=f"**{label}:** {flag} {display}\n\n" + get_translation(ui_code, "PREFERENCES.footer"),
            color=0x2ecc71
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        logger.error(f"Error updating UI language for user {user_id}: {e}")
        await interaction.response.send_message(
            get_translation(current_ui_lang, "ERRORS.database_error"),
            ephemeral=True
        )

# Only keep autocomplete for UI
set_preferences.autocomplete('ui_language')(translated_language_autocomplete)



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
    user_id = interaction.user.id
    ui_lang = await get_user_ui_language(user_id)

    if rating < 1 or rating > 5:
        await interaction.response.send_message(
            get_translation(ui_lang, "FEEDBACK.rating_error"), ephemeral=True
        )
        return

    try:
        user_data = reward_db.get_or_create_user(user_id, interaction.user.display_name)

        if user_data['total_sessions'] < 3:
            sessions_needed = 3 - user_data['total_sessions']
            await interaction.response.send_message(
                get_translation(ui_lang, "FEEDBACK.sessions_needed",
                    sessions_needed=sessions_needed,
                    current_sessions=user_data['total_sessions']),
                ephemeral=True
            )
            return

        from datetime import datetime, timedelta
        now = datetime.now()

        last_feedback = await feedback_db.get_last_feedback_date(user_id)
        if last_feedback:
            last_feedback_date = datetime.fromisoformat(last_feedback).date()
            if last_feedback_date >= now.date():
                tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                time_left = tomorrow - now
                hours_left = int(time_left.total_seconds() // 3600)
                minutes_left = int((time_left.total_seconds() % 3600) // 60)

                await interaction.response.send_message(
                    get_translation(ui_lang, "FEEDBACK.daily_limit",
                        hours_left=hours_left, minutes_left=minutes_left),
                    ephemeral=True
                )
                return

        last_feedback_session = await feedback_db.get_last_feedback_session(user_id)
        if last_feedback_session:
            sessions_since_feedback = user_data['total_sessions'] - last_feedback_session
            if sessions_since_feedback < 3:
                sessions_needed = 3 - sessions_since_feedback
                await interaction.response.send_message(
                    get_translation(ui_lang, "FEEDBACK.session_limit",
                        sessions_needed=sessions_needed,
                        sessions_since_feedback=sessions_since_feedback),
                    ephemeral=True
                )
                return

        await feedback_db.add_feedback(
            user_id=user_id,
            username=interaction.user.display_name,
            rating=rating,
            message=message,
            session_count=user_data['total_sessions']
        )

        current_tier = await tier_handler.get_user_tier_async(user_id)
        feedback_points = {
            'free': 15, 'basic': 20, 'premium': 25, 'pro': 30
        }.get(current_tier, 15)

        detailed_bonus = message and len(message.strip()) >= 20
        if detailed_bonus:
            feedback_points += 10

        reward_db.add_points(
            user_id,
            feedback_points,
            f"Feedback submission ({rating}⭐)" + (" + detailed message bonus" if detailed_bonus else "")
        )

        await reward_db.award_achievement(user_id, 'feedback_provider')

        # Track achievement-related points and notify
        uncashed_points, _ = reward_db.get_uncashed_achievement_points(user_id)
        await notify_uncashed_achievements(user_id, interaction.user.display_name, uncashed_points)

        stars = "⭐" * rating
        color = 0x00ff00 if rating >= 4 else 0xff9900 if rating == 3 else 0xff6b6b

        embed = discord.Embed(
            title=get_translation(ui_lang, "FEEDBACK.thank_you_title"),
            description=f"{stars} **{rating}/5 stars**",
            color=color
        )

        if message:
            embed.add_field(
                name=get_translation(ui_lang, "FEEDBACK.your_message_field"),
                value=f'"{message}"',
                inline=False
            )

        points_text = f"💎 **+{feedback_points} points** earned!"
        if detailed_bonus:
            points_text += "\n🏱 **+10 bonus** for detailed feedback!"

        embed.add_field(
            name=get_translation(ui_lang, "FEEDBACK.reward_field"),
            value=points_text,
            inline=False
        )

        embed.add_field(
            name=get_translation(ui_lang, "FEEDBACK.next_feedback_field"),
            value=get_translation(ui_lang, "FEEDBACK.next_feedback_value"),
            inline=False
        )

        embed.set_footer(text=get_translation(ui_lang, "FEEDBACK.footer"))
        await interaction.response.send_message(embed=embed, ephemeral=True)

        feedback_channel = client.get_channel(1234567890123456789)
        if feedback_channel:
            fields = get_translation(ui_lang, "FEEDBACK.notification_fields")
            notif = discord.Embed(
                title=get_translation(ui_lang, "FEEDBACK.notification_title"),
                color=color
            )
            notif.add_field(name=fields["user"], value=f"{interaction.user.display_name}\n`{user_id}`", inline=True)
            notif.add_field(name=fields["rating"], value=f"{stars} {rating}/5", inline=True)
            notif.add_field(name=fields["sessions"], value=f"{user_data['total_sessions']} total", inline=True)
            notif.add_field(name=fields["context"], value=interaction.guild.name if interaction.guild else "DM", inline=True)
            notif.add_field(name=fields["tier"], value=current_tier.title(), inline=True)
            notif.add_field(name=fields["points_awarded"], value=f"{feedback_points} points", inline=True)

            if message:
                notif.add_field(name=fields["message"], value=message[:1000] + ("..." if len(message) > 1000 else ""), inline=False)
            notif.timestamp = datetime.now()

            await feedback_channel.send(embed=notif)

    except Exception as e:
        logger.error(f"Error in feedback command: {e}")
        await interaction.response.send_message(
            get_translation(ui_lang, "FEEDBACK.error_saving", error=str(e)),
            ephemeral=True
        )

@tree.command(name="reviews", description="View recent feedback and ratings")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def view_reviews(interaction: discord.Interaction):
    user_id = interaction.user.id
    ui_lang = await get_user_ui_language(user_id)

    try:
        stats = await feedback_db.get_stats()
        recent_feedback = await feedback_db.get_all_feedback(limit=10)

        embed = discord.Embed(
            title=get_translation(ui_lang, "REVIEWS.title"),
            color=0x3498db
        )

        if stats["total"] > 0:
            embed.add_field(
                name=get_translation(ui_lang, "REVIEWS.overall_rating_title"),
                value=get_translation(ui_lang, "REVIEWS.overall_rating_value",
                    avg=stats["avg_rating"], total=stats["total"]),
                inline=True
            )

            embed.add_field(
                name=get_translation(ui_lang, "REVIEWS.breakdown_title"),
                value=get_translation(ui_lang, "REVIEWS.breakdown_value",
                    five=stats["five_star"],
                    four=stats["four_star"],
                    three=stats["three_star"],
                    two=stats["two_star"],
                    one=stats["one_star"]
                ),
                inline=True
            )
        else:
            embed.add_field(
                name=get_translation(ui_lang, "REVIEWS.no_reviews_title"),
                value=get_translation(ui_lang, "REVIEWS.no_reviews_value"),
                inline=False
            )

        if recent_feedback:
            recent_text = ""
            for feedback in recent_feedback[:5]:
                stars = "⭐" * feedback["rating"]
                date = feedback["created_at"][:10]
                if feedback["message"]:
                    preview = feedback["message"][:50] + "..." if len(feedback["message"]) > 50 else feedback["message"]
                    recent_text += f"{stars} **{feedback['username']}** ({date})\n*\"{preview}\"*\n\n"
                else:
                    recent_text += f"{stars} **{feedback['username']}** ({date})\n\n"

            embed.add_field(
                name=get_translation(ui_lang, "REVIEWS.recent_reviews_title"),
                value=recent_text[:1024],
                inline=False
            )

        embed.set_footer(text=get_translation(ui_lang, "REVIEWS.footer"))

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(
            get_translation(ui_lang, "REVIEWS.error", error=str(e)),
            ephemeral=True
        )

@tree.command(name="daily", description="Claim your daily point reward")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def daily_reward(interaction: discord.Interaction):
    await track_command_usage(interaction)
    user_id = interaction.user.id
    username = interaction.user.display_name
    
    # Get the user's tier (async)
    user_tier = await tier_handler.get_user_tier_async(user_id)
    
    tier_labels = {
        "free": "Free 🆓",
        "basic": "Basic 🥉", 
        "premium": "Premium 🥈",
        "pro": "Pro 🥇"
    }
    
    tier_colors = {
        "free": 0x95a5a6,
        "basic": 0x3498db,
        "premium": 0xf39c12,
        "pro": 0x9b59b6
    }
    
    # Claim reward with streak
    result = reward_db.claim_daily_reward(user_id, username, user_tier)
    
    if result['success']:
        embed = discord.Embed(
            title="🎁 Daily Reward Claimed!",
            description=f"You earned **{result['points_earned']} points**!",
            color=tier_colors.get(user_tier, 0x95a5a6)
        )
        
        embed.add_field(
            name="💎 Total Points", 
            value=f"{result['total_points']:,}", 
            inline=True
        )
        
        embed.add_field(
            name="⭐ Your Tier", 
            value=tier_labels.get(user_tier, "Free 🆓"), 
            inline=True
        )
        
        embed.add_field(
            name="🔥 Daily Streak",
            value=f"{result['streak_days']} days",
            inline=True
        )
        
        # Show breakdown
        breakdown = f"Base: {result['base_reward']}pts"
        if result.get('streak_bonus', 0) > 0:
            breakdown += f"\nStreak: +{result['streak_bonus']}pts"
        
        embed.add_field(
            name="📊 Breakdown",
            value=breakdown,
            inline=True
        )
        
        embed.add_field(
            name="⏰ Next Claim", 
            value="Tomorrow", 
            inline=True
        )
        
        embed.add_field(
            name="🎯 Next Bonus",
            value=result.get('next_streak_bonus', 'Max reached!'),
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
    else:
        embed = discord.Embed(
            title="❌ Daily Reward",
            description=result['error'],
            color=0xe74c3c
        )
        
        if result.get('next_claim') == 'tomorrow':
            embed.add_field(
                name="⏰ Next Available",
                value="Come back tomorrow for your next daily reward!",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="shop", description="Browse and purchase rewards with points")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def shop(interaction: discord.Interaction):
    await track_command_usage(interaction)
    
    user_id = interaction.user.id
    ui_lang = await get_user_ui_language(user_id)
    
    user_data = reward_db.get_or_create_user(user_id, interaction.user.display_name)
    
    embed = discord.Embed(
        title=get_translation(ui_lang, "SHOP.title"),
        description=get_translation(ui_lang, "SHOP.description", points=f"{user_data['points']:,}"),
        color=0x3498db
    )
    
    for reward_id, reward in REWARDS.items():
        status = ""
        if reward_db.has_active_reward(user_id, reward_id):
            status = get_translation(ui_lang, "SHOP.status_active")
        elif user_data['points'] < reward['cost']:
            status = get_translation(ui_lang, "SHOP.status_not_enough")
        
        field_name = f"{reward['name']} - {reward['cost']} 💎{status}"
        field_value = get_translation(ui_lang, "SHOP.field_duration", hours=reward['duration_hours'])
        
        embed.add_field(
            name=field_name,
            value=field_value,
            inline=False
        )
    
    embed.set_footer(text=get_translation(ui_lang, "SHOP.footer"))
    
    await interaction.response.send_message(embed=embed, ephemeral=True)
# Assuming these dicts hold active features and multipliers keyed by user_id
# Each entry: { reward_id: expires_at }
user_features = {}
user_multipliers = {}

async def grant_feature(user_id: int, reward_id: str, expires_at):
    """
    Grants a feature reward to a user, with expiration.
    """
    # Initialize user's feature dict if missing
    if user_id not in user_features:
        user_features[user_id] = {}

    # Add or update feature expiration
    user_features[user_id][reward_id] = expires_at

    # You can add more logic here to enable feature effects, e.g. update DB

    return True, f"Feature '{reward_id}' granted until {expires_at.strftime('%Y-%m-%d %H:%M:%S')}"

async def grant_multiplier(user_id: int, reward_id: str, expires_at):
    """
    Grants a multiplier reward to a user, with expiration.
    """
    # Initialize user's multiplier dict if missing
    if user_id not in user_multipliers:
        user_multipliers[user_id] = {}

    # Add or update multiplier expiration
    user_multipliers[user_id][reward_id] = expires_at

    # Add logic here if needed to apply multiplier effects in your point calculations

    return True, f"Multiplier '{reward_id}' granted until {expires_at.strftime('%Y-%m-%d %H:%M:%S')}"

@tree.command(name="buy", description="Purchase a reward with points")
@app_commands.describe(reward="The reward you want to purchase")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def buy_reward(interaction: discord.Interaction, reward: str):
    await track_command_usage(interaction)
    
    user_id = interaction.user.id
    ui_lang = await get_user_ui_language(user_id)
    
    # Find reward by name or ID (case insensitive)
    reward_id = None
    for r_id, r_data in REWARDS.items():
        if reward.lower() in r_data['name'].lower() or reward.lower() == r_id.lower():
            reward_id = r_id
            break

    if not reward_id:
        embed = discord.Embed(
            title=get_translation(ui_lang, "BUY.error_invalid_title"),
            description=get_translation(ui_lang, "BUY.error_invalid_description", reward=reward),
            color=0xe74c3c
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    # Attempt purchase
    result = reward_db.purchase_reward(user_id, reward_id)

    if not result['success']:
        embed = discord.Embed(
            title=get_translation(ui_lang, "BUY.error_failed_title"),
            description=get_translation(ui_lang, "BUY.error_failed_description", error=result['error']),
            color=0xe74c3c
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    reward_data = result['reward']
    expires_at = result['expires_at']
    reward_type = reward_data.get('type', '')

    apply_success = True
    apply_message = ""

    # Apply reward effect based on type
    if reward_type in ['basic', 'premium', 'pro']:
        # Pass reward_id instead of reward_type, since your new method extracts tier from reward_id
        apply_success, apply_message = await tier_handler.upgrade_user_tier(user_id, reward_id, expires_at)


    elif reward_type in ['feature', 'beta_feature']:
        # You need to implement grant_feature yourself; placeholder here:
        apply_success, apply_message = await grant_feature(user_id, reward_id, expires_at)

    elif reward_type == 'multiplier':
        # You need to implement grant_multiplier yourself; placeholder here:
        apply_success, apply_message = await grant_multiplier(user_id, reward_id, expires_at)

    elif reward_type == 'bundle':
        includes = reward_data.get('includes', [])
        for included_reward_id in includes:
            included_reward = REWARDS[included_reward_id]
            inc_type = included_reward.get('type', '')
            if inc_type in ['basic', 'premium', 'pro']:
                success, msg = tier_handler.upgrade_user_tier(user_id, inc_type, expires_at)
            elif inc_type in ['feature', 'beta_feature']:
                success, msg = await grant_feature(user_id, included_reward_id, expires_at)
            elif inc_type == 'multiplier':
                success, msg = await grant_multiplier(user_id, included_reward_id, expires_at)
            else:
                success, msg = True, "Cosmetic or unsupported reward in bundle"
            if not success:
                apply_success = False
                apply_message += f"\nFailed to apply {included_reward['name']}: {msg}"

    else:
        # Cosmetic reward - no backend action needed
        apply_success = True
        apply_message = "Cosmetic reward granted."

    # Compose embed to send feedback
    embed = discord.Embed(
        title=get_translation(ui_lang, "BUY.success_title") if apply_success else get_translation(ui_lang, "BUY.error_failed_title"),
        description=get_translation(ui_lang, "BUY.success_description", reward_name=reward_data['name']) if apply_success else apply_message,
        color=0x2ecc71 if apply_success else 0xe74c3c
    )

    embed.add_field(
        name=get_translation(ui_lang, "BUY.field_points_spent"),
        value=f"{reward_data['cost']:,}",
        inline=True
    )

    embed.add_field(
        name=get_translation(ui_lang, "BUY.field_points_remaining"),
        value=f"{result['points_remaining']:,}",
        inline=True
    )

    if expires_at:
        embed.add_field(
            name=get_translation(ui_lang, "BUY.field_expires"),
            value=f"<t:{int(expires_at.timestamp())}:R>",
            inline=True
        )

    embed.add_field(
        name=get_translation(ui_lang, "BUY.field_description"),
        value=reward_data['description'],
        inline=False
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

# Add autocomplete for buy command
async def reward_autocomplete(interaction: discord.Interaction, current: str) -> list[app_commands.Choice[str]]:
    choices = []
    for reward_id, reward_data in REWARDS.items():
        if current.lower() in reward_data['name'].lower():
            choices.append(app_commands.Choice(
                name=f"{reward_data['name']} - {reward_data['cost']} 💎",
                value=reward_id
            ))
    return choices[:25]

buy_reward.autocomplete('reward')(reward_autocomplete)

@tree.command(name="leaderboard", description="View the top users by points")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def leaderboard(interaction: discord.Interaction):
    await track_command_usage(interaction)

    user_id = interaction.user.id
    ui_lang = await get_user_ui_language(user_id)

    top_users = reward_db.get_leaderboard(10)
    user_rank = reward_db.get_user_rank(user_id)

    embed = discord.Embed(
        title=get_translation(ui_lang, "LEADERBOARD.title"),
        description=get_translation(ui_lang, "LEADERBOARD.description"),
        color=0xf1c40f
    )

    if not top_users:
        embed.description = get_translation(ui_lang, "LEADERBOARD.no_users")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return

    leaderboard_text = ""
    for i, user_data in enumerate(top_users, 1):
        rank_emoji = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")

        # Try to refresh the username from Discord
        try:
            member = await client.fetch_user(user_data["user_id"])
            username = member.display_name or member.name
        except:
            username = user_data.get("username", f"User {user_data['user_id']}")

        highlight = "**" if user_data['user_id'] == user_id else ""
        leaderboard_text += f"{rank_emoji} {highlight}{username}{highlight} - {user_data['points']:,} 💎\n"

    embed.add_field(
        name=get_translation(ui_lang, "LEADERBOARD.field_top_users"),
        value=leaderboard_text,
        inline=False
    )

    if user_rank and user_rank > 10:
        embed.add_field(
            name=get_translation(ui_lang, "LEADERBOARD.field_your_rank"),
            value=f"#{user_rank}",
            inline=True
        )

    total_users = reward_db.get_total_users()
    total_points = reward_db.get_total_points_distributed()

    embed.add_field(
        name=get_translation(ui_lang, "LEADERBOARD.field_statistics"),
        value=(
            get_translation(ui_lang, "LEADERBOARD.stat_total_users", total_users=f"{total_users:,}") + "\n" +
            get_translation(ui_lang, "LEADERBOARD.stat_total_points", total_points=f"{total_points:,}")
        ),
        inline=False
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="profile", description="View your complete translation profile and statistics")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def profile(interaction: discord.Interaction):
    await track_command_usage(interaction)

    try:
        user_id = interaction.user.id
        username = interaction.user.display_name
        ui_lang = await get_user_ui_language(user_id)

        reward_user_data = reward_db.get_or_create_user(user_id, username)
        achievement_stats = achievement_db.get_user_stats(user_id)
        user_achievements = achievement_db.get_user_achievements(user_id)

        try:
            db_stats = await db.get_user_stats(user_id)
        except:
            db_stats = {}

        try:
            limits = await tier_handler.get_limits(user_id) if asyncio.iscoroutinefunction(tier_handler.get_limits) else tier_handler.get_limits(user_id)
        except:
            limits = {'text_limit': 50, 'voice_limit': 5}

        is_free = user_id in getattr(tier_handler, 'free_users', [])
        is_basic = user_id in getattr(tier_handler, 'basic_users', [])
        is_premium = user_id in getattr(tier_handler, 'premium_users', [])
        is_pro = user_id in getattr(tier_handler, 'pro_users', [])

        if is_pro:
            tier_key = "pro"
        elif is_premium:
            tier_key = "premium"
        elif is_basic:
            tier_key = "basic"
        else:
            tier_key = "free"

        total_points = reward_db.get_total_points_including_achievements(user_id)
        uncashed_points, _ = reward_db.get_uncashed_achievement_points(user_id)

        from achievement_system import get_rank_from_points, get_rarest_achievement, get_next_milestone, RARITY_INFO
        rank_info = get_rank_from_points(total_points)

        # Re-apply translation for rank after calling the non-internationalized get_rank_from_points
        rank_display_name = get_translation(ui_lang, f"RANKS.{rank_info['name']}", default=f"{rank_info['emoji']} {rank_info['name']}")

        if not rank_info or rank_info.get("emoji") == "⚪":
            rank_info = {
                "name": get_translation(ui_lang, "PROFILE.unranked", default="Unranked"),
                "emoji": "🔘",
                "color": 0x95a5a6
            }

        total_translations = max(
            db_stats.get('total_translations', 0),
            achievement_stats.get('total_translations', 0),
            reward_user_data.get('total_translations', 0)
        )
        voice_sessions = max(
            achievement_stats.get('voice_sessions', 0),
            reward_user_data.get('total_sessions', 0)
        )
        total_usage_hours = reward_user_data.get('total_usage_hours', 0.0)
        languages_used = achievement_stats.get('languages_used', [])

        embed = discord.Embed(
            title=get_translation(ui_lang, "PROFILE.title", username=username),
            color=rank_info.get('color', 0x3498db)
        )

        if interaction.user.avatar:
            embed.set_thumbnail(url=interaction.user.avatar.url)

        points_display = get_translation(ui_lang, "PROFILE.points_activity", points=f"{reward_user_data.get('points', 0):,}")
        if uncashed_points > 0:
            points_display += "\n" + get_translation(ui_lang, "PROFILE.points_achievement", points=f"{uncashed_points:,}")
            points_display += "\n" + get_translation(ui_lang, "PROFILE.points_total", points=f"{total_points:,}")

        embed.add_field(
            name=get_translation(ui_lang, "PROFILE.rank_title"),
            value=f"**{rank_display_name}**\n{points_display}",
            inline=True
        )

        embed.add_field(
            name=get_translation(ui_lang, "PROFILE.usage_title"),
            value=get_translation(
                ui_lang,
                "PROFILE.usage_value",
                translations=f"{total_translations:,}",
                sessions=f"{voice_sessions:,}",
                hours=f"{total_usage_hours:.1f}",
                languages=len(languages_used)
            ),
            inline=True
        )

        try:
            text_limit_val = limits.get("text_limit", 50)
            voice_limit_val = limits.get("voice_limit", 5)

            text_limit_display = get_translation(ui_lang, "PROFILE.limit_unlimited") if text_limit_val == float("inf") else f"{text_limit_val:,} chars"

            daily_usage = await db.get_daily_usage(user_id)
            used_voice = daily_usage.get("voice_seconds", 0)
            remaining_voice_seconds = max(0, voice_limit_val - used_voice)

            if voice_limit_val == float("inf"):
                remaining_voice = get_translation(ui_lang, "PROFILE.limit_unlimited")
            else:
                minutes = int(remaining_voice_seconds // 60)
                seconds = int(remaining_voice_seconds % 60)
                remaining_voice = f"{minutes} min {seconds} sec"

            remaining_display = get_translation(
                ui_lang,
                "PROFILE.limit_remaining",
                chars=text_limit_display,
                voice=remaining_voice
            )
        except:
            remaining_display = "N/A"

        embed.add_field(
            name=get_translation(ui_lang, "PROFILE.limit_title"),
            value=remaining_display,
            inline=True
        )

        # Add media limits under the tier limits section with emoji
        MEDIA_LIMITS_MB = {
            "free": 4,      # below 8MB Discord limit
            "basic": 8,
            "premium": 20,
            "pro": 50       # Nitro user cap
        }
        media_limit_mb = MEDIA_LIMITS_MB.get(tier_key, 4)

        tier_emoji = {
            "pro": "💎",
            "premium": "💠",
            "basic": "🥉",
            "free": "🪙"
        }.get(tier_key, "🪙")

        text_limit_display = "Unlimited" if text_limit_val == float("inf") else f"{text_limit_val:,} chars"
        voice_limit_display = "Unlimited" if voice_limit_val == float("inf") else f"{voice_limit_val:,} seconds"

        tier_limits_lines = [
            f"📝 Text Limit: {text_limit_display}",
            f"🎹 Voice Limit: {voice_limit_display}",
            f"🖼️ Media Upload Limit: {media_limit_mb} MB"
        ]

        embed.add_field(
            name=get_translation(ui_lang, "PROFILE.tier_limits_title"),
            value="\n".join(tier_limits_lines),
            inline=False
        )

        embed.add_field(
            name=get_translation(ui_lang, "PROFILE.current_tier_title"),
            value=f"{tier_emoji} {tier_key.capitalize()}",
            inline=False
        )

        if user_achievements:
            achievement_text = get_translation(ui_lang, "PROFILE.achievements_value", count=len(user_achievements))
            rarest = get_rarest_achievement(user_id)
            if rarest:
                rarity_display = RARITY_INFO.get(rarest["rarity"], rarest["rarity"])

            milestone = get_next_milestone(total_points)
            if milestone:
                current = milestone.get('current', total_points)
                required = milestone.get('required', milestone.get('next_rank_points', '?'))
                bar_len = 10
                ratio = min(current / required, 1.0) if required else 0
                filled = int(bar_len * ratio)
                bar = "█" * filled + "░" * (bar_len - filled)
                achievement_text += f"\nProgress: {bar} {current}/{required} XP"
        else:
            achievement_text = get_translation(ui_lang, "PROFILE.achievements_value", count=0)

        embed.add_field(
            name=get_translation(ui_lang, "PROFILE.achievements_title"),
            value=achievement_text,
            inline=True
        )

        if languages_used:
            top_lang = languages_used[0]
            top_name = get_translation(ui_lang, f"LANGUAGES.{top_lang}", default=languages.get(top_lang, top_lang))
            top_flag = flag_mapping.get(top_lang, "🌐")
            embed.add_field(
                name=get_translation(ui_lang, "PROFILE.most_used_title"),
                value=get_translation(ui_lang, "PROFILE.most_used_value", flag=top_flag, language=top_name),
                inline=True
            )
        else:
            embed.add_field(
                name=get_translation(ui_lang, "PROFILE.most_used_title"),
                value=get_translation(ui_lang, "PROFILE.languages_empty"),
                inline=True
            )

        if languages_used:
            lang_lines = []
            for code in languages_used[:10]:
                name = get_translation(ui_lang, f"LANGUAGES.{code}", default=languages.get(code, code))
                flag = flag_mapping.get(code, "🌐")
                lang_lines.append(f"{flag} {name}")
            lang_value = "\n".join(lang_lines)
        else:
            lang_value = get_translation(ui_lang, "PROFILE.languages_empty")

        embed.add_field(
            name=get_translation(ui_lang, "PROFILE.languages_title"),
            value=lang_value,
            inline=False
        )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    except Exception as e:
        logger.error(f"/profile error: {e}")
        try:
            ui_lang = await get_user_ui_language(interaction.user.id)
        except:
            ui_lang = "en"
        error_embed = discord.Embed(
            title=get_translation(ui_lang, "PROFILE.error_title"),
            description=get_translation(ui_lang, "PROFILE.error_desc", error=str(e)),
            color=0xFF0000
        )
        await interaction.response.send_message(embed=error_embed, ephemeral=True)

class ProfileView(discord.ui.View):
    def __init__(self, user_id: int, is_premium: bool):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.is_premium = is_premium

    @discord.ui.button(label="🎯 Achievements", style=discord.ButtonStyle.primary)
    async def view_achievements(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Get achievement data from the proper database
            user_achievements = achievement_db.get_user_achievements(self.user_id)
            achievement_stats = achievement_db.get_user_stats(self.user_id)
            
            embed = discord.Embed(
                title=f"🏆 {interaction.user.display_name}'s Achievements",
                description="Your achievement progress and unlocked rewards:",
                color=0xf1c40f
            )
            
            # Achievement overview
            from achievement_system import ACHIEVEMENTS
            total_achievements = len(ACHIEVEMENTS)
            unlocked_count = len(user_achievements)
            completion_percentage = int((unlocked_count / total_achievements) * 100) if total_achievements > 0 else 0
            
            embed.add_field(
                name="📊 Achievement Overview",
                value=(
                    f"**Unlocked:** {unlocked_count}/{total_achievements} ({completion_percentage}%)\n"
                    f"**Total Points:** {achievement_stats.get('total_points', 0):,}\n"
                    f"**Translations:** {achievement_stats.get('total_translations', 0):,}\n"
                    f"**Voice Sessions:** {achievement_stats.get('voice_sessions', 0):,}"
                ),
                inline=False
            )
            
            # Recent achievements (last 5)
            if user_achievements:
                recent_achievements = user_achievements[:5]  # Most recent first
                recent_text = ""
                for ach in recent_achievements:
                    ach_name = ach.get('name', 'Unknown Achievement')
                    ach_rarity = ach.get('rarity', 'Common')
                    ach_points = ach.get('points', 0)
                    
                    # Get rarity emoji
                    from achievement_system import RARITY_INFO
                    rarity_emoji = RARITY_INFO.get(ach_rarity, {}).get('emoji', '⚪')
                    
                    recent_text += f"{rarity_emoji} **{ach_name}** (+{ach_points} pts)\n"
                
                embed.add_field(
                    name="🎉 Recent Achievements",
                    value=recent_text,
                    inline=False
                )
            else:
                embed.add_field(
                    name="🎯 Get Started",
                    value="Complete your first translation to unlock achievements!",
                    inline=False
                )
            
            # Progress towards next achievements
            progress_text = ""
            translations = achievement_stats.get('total_translations', 0)
            voice_sessions = achievement_stats.get('voice_sessions', 0)
            unique_languages = len(achievement_stats.get('languages_used', []))
            
            # Check some key achievement progress
            if translations < 5:
                progress_text += f"📝 **Getting the Hang of It**: {translations}/5 translations\n"
            elif translations < 25:
                progress_text += f"🎯 **Regular User**: {translations}/25 translations\n"
            elif translations < 100:
                progress_text += f"👑 **Translation Expert**: {translations}/100 translations\n"
            
            if voice_sessions < 5:
                progress_text += f"🎙️ **Voice User**: {voice_sessions}/5 voice sessions\n"
            elif voice_sessions < 15:
                progress_text += f"📻 **Voice Enthusiast**: {voice_sessions}/15 voice sessions\n"
            
            if unique_languages < 3:
                progress_text += f"🌍 **Language Explorer**: {unique_languages}/3 languages\n"
            elif unique_languages < 10:
                progress_text += f"🌎 **Polyglot**: {unique_languages}/10 languages\n"
            
            if progress_text:
                embed.add_field(
                    name="📈 Progress Towards Next",
                    value=progress_text,
                    inline=False
                )
            
            embed.add_field(
                name="💡 Tip",
                value="Use `/achievements` command for the full interactive achievement system with categories!",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Achievements redirect error: {e}")
            await interaction.response.send_message("❌ Error loading achievements. Use `/achievements` command directly.", ephemeral=True)

    @discord.ui.button(label="🛍️ Rewards Shop", style=discord.ButtonStyle.success)
    async def rewards_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Get user data for points display
            user_data = reward_db.get_or_create_user(self.user_id, interaction.user.display_name)
            total_points = reward_db.get_total_points_including_achievements(self.user_id)
            uncashed_points, _ = reward_db.get_uncashed_achievement_points(self.user_id)
            
            embed = discord.Embed(
                title="🛍️ Rewards Shop Preview",
                description=f"Your available points: **{total_points:,}**",
                color=0x2ecc71
            )
            
            if uncashed_points > 0:
                embed.description += f"\n💡 You have **{uncashed_points:,}** uncashed achievement points!"
            
            # Show popular items from different categories
            from reward_system import REWARDS
            
            # Tier upgrades
            embed.add_field(
                name="⭐ Tier Upgrades",
                value=(
                    "🥉 **1-Day Basic Access** - 50 pts\n"
                    "🥈 **1-Day Premium Access** - 150 pts\n"
                    "🥇 **1-Day Pro Access** - 250 pts\n"
                    "🥈 **7-Day Premium Access** - 800 pts"
                ),
                inline=True
            )
            
            # Individual features
            embed.add_field(
                name="🎯 Individual Features",
                value=(
                    "📚 **Translation History** - 40 pts\n"
                    "📈 **Extended Character Limit** - 60 pts\n"
                    "🎤 **Extended Voice Time** - 80 pts\n"
                    "⚡ **Priority Processing** - 35 pts"
                ),
                inline=True
            )
            
            # Beta features
            embed.add_field(
                name="🚀 Beta & Special",
                value=(
                    "🚀 **Enhanced Voice V2 (1 Day)** - 50 pts\n"
                    "🚀 **Enhanced Voice V2 (7 Days)** - 300 pts\n"
                    "💰 **2x Point Multiplier** - 75 pts\n"
                    "💎 **3x Point Multiplier** - 150 pts"
                ),
                inline=True
            )
            
            # Value bundles
            embed.add_field(
                name="🎁 Value Bundles",
                value=(
                    "🎁 **Starter Bundle** - 100 pts (33% off)\n"
                    "🎉 **Premium Bundle** - 300 pts (29% off)\n"
                    "👑 **Ultimate Bundle** - 750 pts (27% off)"
                ),
                inline=False
            )
            
            embed.add_field(
                name="💡 How to Shop",
                value="Use `/shop` command for the full interactive shopping experience with detailed descriptions and instant purchases!",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Shop redirect error: {e}")
            await interaction.response.send_message("❌ Error loading shop. Use `/shop` command directly.", ephemeral=True)

    @discord.ui.button(label="🎁 Daily Reward", style=discord.ButtonStyle.secondary)
    async def daily_reward(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            user_data = reward_db.get_or_create_user(self.user_id, interaction.user.display_name)
            
            # Check if daily reward is available
            last_claim = user_data.get('last_daily_claim')
            can_claim = True
            hours_left = 0
            
            if last_claim:
                try:
                    from datetime import datetime, date
                    # Handle both date and datetime formats
                    if isinstance(last_claim, str):
                        try:
                            # Try parsing as date first
                            last_claim_date = datetime.strptime(last_claim, '%Y-%m-%d').date()
                        except ValueError:
                            # Try parsing as datetime
                            last_claim_date = datetime.fromisoformat(last_claim).date()
                    else:
                        last_claim_date = last_claim
                    
                    today = date.today()
                    
                    if last_claim_date >= today:
                        can_claim = False
                        # Calculate hours until next day
                        now = datetime.now()
                        tomorrow = datetime.combine(today, datetime.min.time()) + timedelta(days=1)
                        hours_left = (tomorrow - now).total_seconds() / 3600
                except Exception as e:
                    logger.error(f"Error parsing last claim date: {e}")
                    can_claim = True
            
            if can_claim:
                # Calculate reward amount
                base_reward = 25 if self.is_premium else 10
                
                embed = discord.Embed(
                    title="🎁 Daily Reward Available!",
                    description=f"Claim your daily reward of **{base_reward} points**!",
                    color=0x2ecc71
                )
                
                embed.add_field(
                    name="💎 Today's Reward",
                    value=(
                        f"**Base Reward:** {base_reward} points\n"
                        f"**Bonus:** {'Premium bonus included!' if self.is_premium else 'Upgrade to Premium for bigger rewards!'}\n"
                        f"**Streak Bonus:** Build streaks for extra points!"
                    ),
                    inline=False
                )
                
                embed.add_field(
                    name="🚀 How to Claim",
                    value="Use `/daily` command to claim your reward and start building your streak!",
                    inline=False
                )
            else:
                # Format remaining time properly
                if hours_left >= 1:
                    time_display = f"{hours_left:.1f} hours"
                else:
                    minutes_left = hours_left * 60
                    time_display = f"{minutes_left:.0f} minutes"
                
                embed = discord.Embed(
                    title="🎁 Daily Reward",
                    description=f"Next reward available in **{time_display}**",
                    color=0x95a5a6
                )
                
                # Get streak info
                daily_streak = user_data.get('daily_streak', 0)
                embed.add_field(
                    name="📊 Current Streak",
                    value=f"**{daily_streak}** days consecutive",
                    inline=True
                )
                
                next_reward = 25 if self.is_premium else 10
                embed.add_field(
                    name="💎 Next Reward",
                    value=f"**{next_reward}** points + streak bonus",
                    inline=True
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Daily reward redirect error: {e}")
            await interaction.response.send_message("❌ Error checking daily reward. Use `/daily` command directly.", ephemeral=True)

    @discord.ui.button(label="📊 Detailed Stats", style=discord.ButtonStyle.secondary)
    async def detailed_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Get comprehensive user data
            reward_user_data = reward_db.get_or_create_user(self.user_id, interaction.user.display_name)
            achievement_stats = achievement_db.get_user_stats(self.user_id)
            
            try:
                db_stats = await db.get_user_stats(self.user_id)
            except Exception:
                db_stats = {'total_translations': 0, 'monthly_translations': 0, 'monthly_chars': 0, 'monthly_voice': 0}
            
            guild_id = interaction.guild_id
            
            embed = discord.Embed(
                title="📊 Detailed Statistics",
                description=f"Complete stats for {interaction.user.display_name}",
                color=0x3498db
            )
            
            # Translation Statistics - use the highest values from all sources
            total_translations = max(
                db_stats.get('total_translations', 0),
                achievement_stats.get('total_translations', 0),
                reward_user_data.get('total_translations', 0)
            )
            
            monthly_translations = db_stats.get('monthly_translations', 0)
            monthly_chars = db_stats.get('monthly_chars', 0)
            
            embed.add_field(
                name="📝 Translation Statistics",
                value=(
                    f"**Total Translations:** {total_translations:,}\n"
                    f"**This Month:** {monthly_translations:,}\n"
                    f"**Characters Translated:** {monthly_chars:,}\n"
                    f"**Voice Sessions:** {achievement_stats.get('voice_sessions', 0):,}"
                ),
                inline=False
            )
            
            # Usage Statistics with proper time formatting
            total_hours = reward_user_data.get('total_usage_hours', 0.0)
            total_sessions = max(
                reward_user_data.get('total_sessions', 0),
                achievement_stats.get('voice_sessions', 0)
            )
            
            if total_sessions > 0:
                avg_session_hours = total_hours / total_sessions
                if avg_session_hours >= 1:
                    avg_session_display = f"{avg_session_hours:.1f} hours"
                else:
                    avg_session_minutes = avg_session_hours * 60
                    avg_session_display = f"{avg_session_minutes:.1f} minutes"
            else:
                avg_session_display = "N/A"
            
            embed.add_field(
                name="⏱️ Usage Statistics",
                value=(
                    f"**Total Usage Time:** {total_hours:.1f} hours\n"
                                        f"**Total Sessions:** {total_sessions:,}\n"
                    f"**Average Session:** {avg_session_display}\n"
                    f"**Monthly Voice Time:** {db_stats.get('monthly_voice', 0) / 60:.1f} minutes"
                ),
                inline=False
            )
            
            # Current Session Info (if active)
            if guild_id and guild_id in voice_translation_sessions:
                session = voice_translation_sessions[guild_id]
                if 'session_start' in session:
                    session_duration_seconds = (datetime.now() - session['session_start']).total_seconds()
                    session_duration_minutes = session_duration_seconds / 60
                    session_duration_hours = session_duration_seconds / 3600
                    
                    # Format current session duration
                    if session_duration_hours >= 1:
                        session_display = f"{session_duration_hours:.1f} hours"
                    elif session_duration_minutes >= 1:
                        session_display = f"{session_duration_minutes:.1f} minutes"
                    else:
                        session_display = f"{session_duration_seconds:.0f} seconds"
                    
                    # Calculate remaining time
                    try:
                        if hasattr(tier_handler, 'get_limits'):
                            if asyncio.iscoroutinefunction(tier_handler.get_limits):
                                limits = await tier_handler.get_limits(self.user_id)
                            else:
                                limits = tier_handler.get_limits(self.user_id)
                        else:
                            limits = {'voice_limit': 5}
                        
                        voice_limit_seconds = limits.get('voice_limit', 5) * 60
                        if voice_limit_seconds == float('inf'):
                            remaining_display = "Unlimited"
                        else:
                            remaining_seconds = max(0, voice_limit_seconds - session_duration_seconds)
                            remaining_minutes = remaining_seconds / 60
                            remaining_hours = remaining_seconds / 3600
                            
                            if remaining_hours >= 1:
                                remaining_display = f"{remaining_hours:.1f} hours"
                            elif remaining_minutes >= 1:
                                remaining_display = f"{remaining_minutes:.1f} minutes"
                            else:
                                remaining_display = f"{remaining_seconds:.0f} seconds"
                    except Exception as e:
                        logger.error(f"Error calculating remaining time: {e}")
                        remaining_display = "Unknown"
                    
                    # Check if voice client is connected
                    is_connected = (session.get('voice_client') and 
                                  session['voice_client'].is_connected())
                    
                    embed.add_field(
                        name="🎤 Current Voice Session",
                        value=(
                            f"**Duration:** {session_display}\n"
                            f"**Remaining:** {remaining_display}\n"
                            f"**Status:** {'🟢 Active' if is_connected else '🔴 Inactive'}"
                        ),
                        inline=False
                    )
            
            # Language Statistics
            languages_used = achievement_stats.get('languages_used', [])
            if languages_used:
                lang_text = ""
                for i, lang_code in enumerate(languages_used[:10]):  # Top 10
                    try:
                        lang_name = languages.get(lang_code, lang_code)
                        flag = flag_mapping.get(lang_code, '🌐')
                        lang_text += f"{flag} {lang_name}\n"
                    except Exception:
                        lang_text += f"🌐 {lang_code}\n"
                
                if len(languages_used) > 10:
                    lang_text += f"... and {len(languages_used) - 10} more"
                
                embed.add_field(
                    name=f"🌍 Languages Used ({len(languages_used)} total)",
                    value=lang_text,
                    inline=False
                )
            
            # Points and Rewards
            activity_points = reward_user_data.get('points', 0)
            total_earned = reward_user_data.get('total_earned', activity_points)
            achievement_points = achievement_stats.get('total_points', 0)
            
            embed.add_field(
                name="💎 Points & Rewards",
                value=(
                    f"**Activity Points:** {activity_points:,}\n"
                    f"**Achievement Points:** {achievement_points:,}\n"
                    f"**Total Points Earned:** {total_earned:,}\n"
                    f"**Daily Streak:** {reward_user_data.get('daily_streak', 0)} days"
                ),
                inline=False
            )
            
            # Account Information
            created_date = reward_user_data.get('created_at', 'Unknown')
            if created_date != 'Unknown':
                try:
                    created_dt = datetime.fromisoformat(created_date)
                    time_since_creation = datetime.now() - created_dt
                    days_active = time_since_creation.days
                    
                    embed.add_field(
                        name="📅 Account Information",
                        value=(
                            f"**Member Since:** {created_dt.strftime('%B %d, %Y')}\n"
                            f"**Days Active:** {days_active}\n"
                            f"**Account Type:** {'Premium ⭐' if self.is_premium else 'Free 🆓'}\n"
                            f"**First Use:** {achievement_stats.get('first_use_date', 'Unknown')}"
                        ),
                        inline=False
                    )
                except Exception as e:
                    logger.error(f"Error parsing created_at: {e}")
            
            # Daily usage breakdown
            try:
                daily_usage = await db.get_daily_usage(self.user_id)
                embed.add_field(
                    name="📅 Today's Usage",
                    value=(
                        f"**Characters Used:** {daily_usage.get('text_chars', 0):,}\n"
                        f"**Voice Time Used:** {daily_usage.get('voice_seconds', 0) / 60:.1f} minutes\n"
                        f"**Translations Today:** {daily_usage.get('translations', 0):,}"
                    ),
                    inline=False
                )
            except Exception as e:
                logger.error(f"Error getting daily usage: {e}")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Detailed stats error: {e}")
            await interaction.response.send_message("❌ Error loading detailed statistics.", ephemeral=True)

    @discord.ui.button(label="⚙️ Settings", style=discord.ButtonStyle.secondary)
    async def user_settings(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            user_data = reward_db.get_or_create_user(self.user_id, interaction.user.display_name)
            
            embed = discord.Embed(
                title="⚙️ User Settings & Preferences",
                description="Manage your translation preferences and settings",
                color=0x95a5a6
            )
            
            # Current Settings
            hide_original = self.user_id in hidden_sessions
            auto_translate_active = self.user_id in auto_translate_users
            
            embed.add_field(
                name="🎛️ Current Settings",
                value=(
                    f"**Hide Original Text:** {'✅ Enabled' if hide_original else '❌ Disabled'}\n"
                    f"**Auto Translation:** {'✅ Active' if auto_translate_active else '❌ Inactive'}\n"
                    f"**Account Type:** {'⭐ Premium' if self.is_premium else '🆓 Free'}"
                ),
                inline=False
            )
            
            # Auto-translate details if active
            if auto_translate_active:
                settings = auto_translate_users[self.user_id]
                source_lang = settings.get('source', 'auto')
                target_lang = settings.get('target', 'en')
                
                source_name = "Auto-detect" if source_lang == "auto" else languages.get(source_lang, source_lang)
                target_name = languages.get(target_lang, target_lang)
                source_flag = '🔍' if source_lang == "auto" else flag_mapping.get(source_lang, '🌐')
                target_flag = flag_mapping.get(target_lang, '🌐')
                
                embed.add_field(
                    name="🔄 Auto-Translation Details",
                    value=(
                        f"**From:** {source_flag} {source_name}\n"
                        f"**To:** {target_flag} {target_name}\n"
                        f"**Status:** Active in this server"
                    ),
                    inline=False
                )
            
            # Usage Preferences
            languages_used = achievement_db.get_user_stats(self.user_id).get('languages_used', [])
            most_used_lang = "None"
            if languages_used:
                try:
                    most_used_code = languages_used[0]
                    most_used_lang = languages.get(most_used_code, most_used_code)
                    most_used_flag = flag_mapping.get(most_used_code, '🌐')
                    most_used_lang = f"{most_used_flag} {most_used_lang}"
                except Exception:
                    most_used_lang = "None"
            
            total_translations = max(
                user_data.get('total_translations', 0),
                achievement_db.get_user_stats(self.user_id).get('total_translations', 0)
            )
            voice_sessions = achievement_db.get_user_stats(self.user_id).get('voice_sessions', 0)
            
            embed.add_field(
                name="📊 Usage Preferences",
                value=(
                    f"**Total Commands Used:** {total_translations + voice_sessions:,}\n"
                    f"**Preferred Feature:** {'Voice Chat' if voice_sessions > total_translations else 'Text Translation'}\n"
                    f"**Most Used Language:** {most_used_lang}\n"
                    f"**Languages Explored:** {len(languages_used)}"
                ),
                inline=False
            )
            
            # Quick Actions
            embed.add_field(
                name="🚀 Quick Actions",
                value=(
                    "Use the buttons below to:\n"
                    "• Toggle text visibility settings\n"
                    "• Check auto-translation status\n"
                    "• View premium upgrade options\n"
                    "• Reset your preferences"
                ),
                inline=False
            )
            
            # Privacy Information
            embed.add_field(
                name="🔒 Privacy & Data",
                value=(
                    "• Translation content is not permanently stored\n"
                    "• Only usage statistics and preferences are saved\n"
                    "• Use `/stop` to end all active sessions\n"
                    "• Data helps improve features and user experience"
                ),
                inline=False
            )
            
            # Create settings view
            settings_view = SettingsView(self.user_id, self.is_premium)
            
            await interaction.response.send_message(embed=embed, view=settings_view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Settings error: {e}")
            await interaction.response.send_message("❌ Error loading settings.", ephemeral=True)

    async def on_timeout(self):
        # Disable all buttons when the view times out
        for item in self.children:
            item.disabled = True

class SettingsView(discord.ui.View):
    def __init__(self, user_id: int, is_premium: bool):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.is_premium = is_premium

    @discord.ui.button(label="👁️ Toggle Text Visibility", style=discord.ButtonStyle.primary)
    async def toggle_visibility(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if self.user_id in hidden_sessions:
                hidden_sessions.discard(self.user_id)
                status = "✅ Original text will now be **shown** in translations"
                new_status = "Show"
            else:
                hidden_sessions.add(self.user_id)
                status = "✅ Original text will now be **hidden** in translations"
                new_status = "Hide"
            
            embed = discord.Embed(
                title="👁️ Text Visibility Updated",
                description=status,
                color=0x2ecc71
            )
            
            embed.add_field(
                name="💡 What This Means",
                value=(
                    f"When you translate text, the original message will be "
                    f"{'hidden' if new_status == 'Hide' else 'shown'} in the response. "
                    f"This setting applies to all your future translations."
                ),
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Toggle visibility error: {e}")
            await interaction.response.send_message("❌ Error updating setting.", ephemeral=True)

    @discord.ui.button(label="🔄 Auto-Translation Status", style=discord.ButtonStyle.secondary)
    async def auto_translate_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if self.user_id in auto_translate_users:
                settings = auto_translate_users[self.user_id]
                source_lang = settings.get('source', 'auto')
                target_lang = settings.get('target', 'en')
                
                source_name = "Auto-detect" if source_lang == "auto" else languages.get(source_lang, source_lang)
                target_name = languages.get(target_lang, target_lang)
                source_flag = '🔍' if source_lang == "auto" else flag_mapping.get(source_lang, '🌐')
                target_flag = flag_mapping.get(target_lang, '🌐')
                
                embed = discord.Embed(
                    title="🔄 Auto-Translation Active",
                    description=(
                        f"Currently translating from {source_flag} **{source_name}** "
                        f"to {target_flag} **{target_name}**"
                    ),
                    color=0x3498db
                )
                
                embed.add_field(
                    name="ℹ️ How It Works",
                    value=(
                        "All your messages in this server are automatically "
                        "translated and sent to the channel. Other users will "
                        "see the translated version of your messages."
                    ),
                    inline=False
                )
                
                embed.add_field(
                    name="🛑 How to Stop",
                    value="Use `/stop` command to disable auto-translation.",
                    inline=False
                )
            else:
                embed = discord.Embed(
                    title="🔄 Auto-Translation Inactive",
                    description="Auto-translation is currently disabled.",
                    color=0x95a5
                )
                embed = discord.Embed(
                    title="🔄 Auto-Translation Inactive",
                    description="Auto-translation is currently disabled.",
                    color=0x95a5a6
                )
                
                embed.add_field(
                    name="🚀 How to Enable",
                    value=(
                        "Use `/auto` command to set up automatic translation "
                        "of your messages in this server."
                    ),
                    inline=False
                )
                
                embed.add_field(
                    name="💡 What It Does",
                    value=(
                        "When enabled, all your messages will be automatically "
                        "translated and posted to the channel. Perfect for "
                        "communicating across language barriers!"
                    ),
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Auto-translate status error: {e}")
            await interaction.response.send_message("❌ Error checking auto-translation status.", ephemeral=True)

    @discord.ui.button(label="⭐ Premium Info", style=discord.ButtonStyle.success)
    async def premium_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            if self.is_premium:
                embed = discord.Embed(
                    title="⭐ Premium Status",
                    description="You are currently a **Premium** user!",
                    color=0xf1c40f
                )
                
                embed.add_field(
                    name="🎉 Your Premium Benefits",
                    value=(
                        "✅ **Unlimited** character translations\n"
                        "✅ **Unlimited** voice translation time\n"
                        "✅ **Priority** processing speed\n"
                        "✅ **Translation history** access\n"
                        "✅ **Auto-translation** features\n"
                        "✅ **2x** daily reward points\n"
                        "✅ **Enhanced voice** features\n"
                        "✅ **Beta** feature access"
                    ),
                    inline=False
                )
                
                embed.add_field(
                    name="💎 Premium Perks",
                    value=(
                        "• Faster response times\n"
                        "• Access to experimental features\n"
                        "• Priority customer support\n"
                        "• Special premium-only commands"
                    ),
                    inline=False
                )
            else:
                embed = discord.Embed(
                    title="⭐ Upgrade to Premium",
                    description="Unlock the full potential of Muse with Premium!",
                    color=0x3498db
                )
                
                # Current limitations
                embed.add_field(
                    name="🆓 Current (Free) Limits",
                    value=(
                        "• **50 characters** per translation\n"
                        "• **5 minutes** total voice time\n"
                        "• **Basic** processing speed\n"
                        "• **No** translation history\n"
                        "• **10 points** daily reward"
                    ),
                    inline=True
                )
                
                # Premium benefits
                embed.add_field(
                    name="⭐ Premium Benefits",
                    value=(
                        "• **Unlimited** characters\n"
                        "• **Unlimited** voice time\n"
                        "• **Priority** processing\n"
                        "• **Full** translation history\n"
                        "• **25 points** daily reward\n"
                        "• **Beta** feature access"
                    ),
                    inline=True
                )
                
                # Pricing tiers
                embed.add_field(
                    name="💰 Pricing Tiers",
                    value=(
                        "🥉 **Basic** - $1/month\n"
                        "• 500 chars, 30min voice\n"
                        "• History & auto-translate\n\n"
                        "🥈 **Premium** - $3/month\n"
                        "• 2000 chars, 2h voice\n"
                        "• Priority & enhanced voice\n\n"
                        "🥇 **Pro** - $5/month\n"
                        "• Unlimited everything\n"
                        "• Beta access & priority support"
                    ),
                    inline=False
                )
                
                embed.add_field(
                    name="🎁 Alternative: Points System",
                    value=(
                        "Can't subscribe? No problem!\n"
                        "• Earn points through daily use\n"
                        "• Purchase temporary upgrades\n"
                        "• Get premium features for hours/days\n"
                        "• Use `/shop` to see options"
                    ),
                    inline=False
                )
                
                embed.add_field(
                    name="🚀 How to Upgrade",
                    value=(
                        "Visit our Ko-fi page to subscribe:\n"
                        "**https://ko-fi.com/musebot**\n\n"
                        "Or use points in `/shop` for temporary access!"
                    ),
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Premium info error: {e}")
            await interaction.response.send_message("❌ Error loading premium information.", ephemeral=True)

    @discord.ui.button(label="🔄 Reset Preferences", style=discord.ButtonStyle.danger)
    async def reset_preferences(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Create confirmation view
            confirm_view = ResetConfirmView(self.user_id)
            
            embed = discord.Embed(
                title="🔄 Reset All Preferences",
                description="⚠️ This will reset all your personal settings to default values.",
                color=0xe74c3c
            )
            
            embed.add_field(
                name="🗑️ What Will Be Reset",
                value=(
                    "• Text visibility preferences\n"
                    "• Auto-translation settings\n"
                    "• Language preferences\n"
                    "• Personal customizations"
                ),
                inline=False
            )
            
            embed.add_field(
                name="✅ What Will NOT Be Reset",
                value=(
                    "• Your points and rewards\n"
                    "• Achievement progress\n"
                    "• Usage statistics\n"
                    "• Premium subscription status"
                ),
                inline=False
            )
            
            embed.add_field(
                name="⚠️ Confirmation Required",
                value="Click the button below to confirm the reset.",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, view=confirm_view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Reset preferences error: {e}")
            await interaction.response.send_message("❌ Error initiating reset.", ephemeral=True)

class ResetConfirmView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=60)
        self.user_id = user_id

    @discord.ui.button(label="✅ Confirm Reset", style=discord.ButtonStyle.danger)
    async def confirm_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Reset user preferences
            if self.user_id in hidden_sessions:
                hidden_sessions.discard(self.user_id)
            
            if self.user_id in auto_translate_users:
                del auto_translate_users[self.user_id]
            
            # Reset database preferences if needed
            try:
                await db.update_user_preferences(self.user_id, source_lang='auto', target_lang='en')
            except Exception as e:
                logger.error(f"Error resetting DB preferences: {e}")
            
            embed = discord.Embed(
                title="✅ Preferences Reset Successfully",
                description="All your personal settings have been reset to default values.",
                color=0x2ecc71
            )
            
            embed.add_field(
                name="🔄 What Was Reset",
                value=(
                    "• Text visibility: **Show original**\n"
                    "• Auto-translation: **Disabled**\n"
                    "• Language preferences: **Auto → English**\n"
                    "• All customizations: **Default**"
                ),
                inline=False
            )
            
            embed.add_field(
                name="💡 Next Steps",
                value=(
                    "You can now reconfigure your settings using:\n"
                    "• `/auto` for auto-translation\n"
                    "• Profile settings for visibility\n"
                    "• Individual commands for preferences"
                ),
                inline=False
            )
            
            # Disable the button
            button.disabled = True
            await interaction.response.edit_message(embed=embed, view=self)
            
        except Exception as e:
            logger.error(f"Confirm reset error: {e}")
            await interaction.response.send_message("❌ Error resetting preferences.", ephemeral=True)

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="❌ Reset Cancelled",
            description="Your preferences have not been changed.",
            color=0x95a5a6
        )
        
        # Disable all buttons
        for item in self.children:
            item.disabled = True
        
        await interaction.response.edit_message(embed=embed, view=self)


@tree.command(name="gift", description="Gift points to another user")
@app_commands.describe(
    user="The user to gift points to",
    amount="Amount of points to gift"
)
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def gift_points(interaction: discord.Interaction, user: discord.User, amount: int):
    await track_command_usage(interaction)
    
    sender_id = interaction.user.id
    receiver_id = user.id
    ui_lang = await get_user_ui_language(sender_id)

    # ❌ Cannot gift to yourself
    if sender_id == receiver_id:
        await interaction.response.send_message(
            get_translation(ui_lang, "GIFT.error_self_gift"),
            ephemeral=True
        )
        return
    
    # ❌ Invalid amount
    if amount < 1:
        await interaction.response.send_message(
            get_translation(ui_lang, "GIFT.error_invalid_amount"),
            ephemeral=True
        )
        return
    
    # Check balance
    sender_data = reward_db.get_or_create_user(sender_id, interaction.user.display_name)
    if sender_data['points'] < amount:
        embed = discord.Embed(
            title=get_translation(ui_lang, "GIFT.error_title"),
            description=get_translation(ui_lang, "GIFT.error_insufficient_points", 
                                         needed=f"{amount:,}", current=f"{sender_data['points']:,}"),
            color=0xe74c3c
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Transfer points
    success = reward_db.transfer_points(
        sender_id,
        receiver_id,
        amount,
        f"Gift from {interaction.user.display_name}"
    )
    
    if success:
        embed = discord.Embed(
            title=get_translation(ui_lang, "GIFT.success_title"),
            description=get_translation(ui_lang, "GIFT.success_description", 
                                         amount=f"{amount:,}", receiver=user.display_name),
            color=0x2ecc71
        )
        
        embed.add_field(
            name=get_translation(ui_lang, "GIFT.field_remaining"),
            value=f"{sender_data['points'] - amount:,}",
            inline=True
        )
        
        embed.add_field(
            name=get_translation(ui_lang, "GIFT.field_thanks"),
            value=get_translation(ui_lang, "GIFT.value_thanks"),
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Try DM-ing the receiver
        try:
            receiver_embed = discord.Embed(
                title=get_translation(ui_lang, "GIFT.notify_title"),
                description=get_translation(ui_lang, "GIFT.notify_description", 
                                             sender=interaction.user.display_name, amount=f"{amount:,}"),
                color=0x2ecc71
            )
            receiver_embed.add_field(
                name=get_translation(ui_lang, "GIFT.notify_shop_title"),
                value=get_translation(ui_lang, "GIFT.notify_shop_description"),
                inline=False
            )
            await user.send(embed=receiver_embed)
        except:
            pass  # user has DMs closed
    else:
        embed = discord.Embed(
            title=get_translation(ui_lang, "GIFT.failed_title"),
            description=get_translation(ui_lang, "GIFT.failed_description"),
            color=0xe74c3c
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="rewards", description="View your active rewards and their expiration times")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def active_rewards(interaction: discord.Interaction):
    await track_command_usage(interaction)
    
    user_id = interaction.user.id
    ui_lang = await get_user_ui_language(user_id)
    active_rewards = reward_db.get_active_rewards(user_id)
    
    embed = discord.Embed(
        title=get_translation(ui_lang, "REWARDS.title"),
        color=0x3498db
    )
    
    if not active_rewards:
        embed.description = get_translation(ui_lang, "REWARDS.no_active")
        embed.add_field(
            name=get_translation(ui_lang, "REWARDS.tip_title"),
            value=get_translation(ui_lang, "REWARDS.tip_value"),
            inline=False
        )
    else:
        for reward in active_rewards:
            expires_timestamp = int(datetime.fromisoformat(reward['expires_at']).timestamp())
            embed.add_field(
                name=get_translation(ui_lang, "REWARDS.reward_name", name=reward["name"]),
                value=get_translation(ui_lang, "REWARDS.reward_expiry", 
                                      relative=f"<t:{expires_timestamp}:R>", 
                                      absolute=f"<t:{expires_timestamp}:f>"),
                inline=False
            )
    
    # Show permanent premium benefits
    if user_id in tier_handler.premium_users:
        embed.add_field(
            name=get_translation(ui_lang, "REWARDS.premium_title"),
            value=get_translation(ui_lang, "REWARDS.premium_value"),
            inline=False
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="transactions", description="View your recent point transactions")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def transactions(interaction: discord.Interaction):
    await track_command_usage(interaction)

    user_id = interaction.user.id
    username = interaction.user.display_name
    ui_lang = await get_user_ui_language(user_id)

    all_transactions = reward_db.get_point_transactions(user_id, 50)  # Pull more to allow filtering
    INCLUDED_TYPES = {"daily", "transfer_in", "transfer_out", "spent", "achievement", "grant"}

    # Filter relevant transactions
    transactions = [
        txn for txn in all_transactions
        if txn["type"] in INCLUDED_TYPES
    ][:15]  # Limit to 15 after filtering

    embed = discord.Embed(
        title=get_translation(ui_lang, "TRANSACTIONS.title"),
        description=get_translation(ui_lang, "TRANSACTIONS.description"),
        color=0x3498db
    )

    if not transactions:
        embed.description = get_translation(ui_lang, "TRANSACTIONS.no_transactions")
    else:
        lines = []
        for txn in transactions:
            amount = txn["amount"]
            sign = "+" if amount > 0 else ""
            amount_str = f"{sign}{amount:,}"

            emoji = {
                "daily": "🎁",
                "transfer_in": "📥",
                "transfer_out": "📤",
                "spent": "🛍️",
                "achievement": "🏅",
                "grant": "💎"
            }.get(txn["type"], "💠")

            try:
                timestamp = datetime.fromisoformat(txn["timestamp"])
                time_str = f"<t:{int(timestamp.timestamp())}:R>"
            except:
                time_str = get_translation(ui_lang, "TRANSACTIONS.unknown_time")

            lines.append(
                get_translation(
                    ui_lang, "TRANSACTIONS.entry_line",
                    emoji=emoji,
                    amount=amount_str,
                    description=txn["description"],
                    time=time_str
                )
            )

        embed.add_field(
            name=get_translation(ui_lang, "TRANSACTIONS.field_history"),
            value="\n".join(lines)[:1024],
            inline=False
        )

    user_data = reward_db.get_or_create_user(user_id, username)
    embed.add_field(
        name=get_translation(ui_lang, "TRANSACTIONS.field_balance"),
        value=get_translation(
            ui_lang, "TRANSACTIONS.balance_value",
            points=f"{user_data['points']:,}"
        ),
        inline=True
    )

    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="invite", description="Get an invite link to add Muse to your server")
async def invite_command(interaction: discord.Interaction):
    """Generate a trackable invite link"""
    try:
        user_id = interaction.user.id
        ui_lang = await get_user_ui_language(user_id)

        # Track who requested the invite (for ambassador achievement)
        store_invite_request(user_id)

        # Create permission scope
        permissions = discord.Permissions(
            read_messages=True,
            send_messages=True,
            embed_links=True,
            attach_files=True,
            read_message_history=True,
            connect=True,
            speak=True,
            view_audit_log=True
        )
        
        invite_url = discord.utils.oauth_url(
            client.user.id,
            permissions=permissions,
            scopes=('bot', 'applications.commands')
        )

        embed = discord.Embed(
            title=get_translation(ui_lang, "INVITE.title"),
            description=get_translation(ui_lang, "INVITE.description"),
            color=0x2ecc71
        )

        embed.add_field(
            name=get_translation(ui_lang, "INVITE.bonus_title"),
            value=get_translation(ui_lang, "INVITE.bonus_description"),
            inline=False
        )

        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label=get_translation(ui_lang, "INVITE.button_label"),
            url=invite_url,
            style=discord.ButtonStyle.link,
            emoji="🚀"
        ))

        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    except Exception as e:
        logger.error(f"Invite command error: {e}")
        await interaction.response.send_message(
            get_translation(ui_lang, "INVITE.error"),
            ephemeral=True
        )


@tree.command(name="vote", description="Support Muse by upvoting on bot lists!")
async def vote_command(interaction: discord.Interaction):
    user_id = interaction.user.id
    ui_lang = await get_user_ui_language(user_id)

    embed = discord.Embed(
        title=get_translation(ui_lang, "VOTE.title"),
        description=get_translation(ui_lang, "VOTE.description"),
        color=0xf1c40f
    )

    embed.add_field(
        name=get_translation(ui_lang, "VOTE.field_title"),
        value=get_translation(ui_lang, "VOTE.field_value"),
        inline=False
    )

    embed.set_footer(text=get_translation(ui_lang, "VOTE.footer"))

    await interaction.response.send_message(embed=embed, ephemeral=True)


@tree.command(name="addbasic", description="[ADMIN] Grant Basic tier access to any Discord user", guild=discord.Object(id=YOUR_SERVER_ID))
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    user="Discord user to grant Basic tier to",
    days="Number of days of Basic access (default: 30)",
    permanent="Make this a permanent upgrade (default: False)"
)
async def add_basic(interaction: discord.Interaction, user: discord.User, days: int = 30, permanent: bool = False):
    if interaction.user.id != YOUR_ADMIN_ID:
        await interaction.response.send_message("❌ Bot owner only!", ephemeral=True)
        return
    
    if days <= 0 and not permanent:
        await interaction.response.send_message("❌ Days must be positive for temporary access!", ephemeral=True)
        return
    
    try:
        from datetime import datetime, timedelta
        
        if permanent:
            expires_at = None
            duration_text = "Permanent"
        else:
            expires_at = datetime.now() + timedelta(days=days)
            duration_text = f"{days} days"
        
        # Grant Basic tier
        await tier_handler.set_user_tier_async(user.id, 'basic', expires_at)
        
        # Get tier limits for display
        limits = tier_handler.get_limits_for_tier('basic')
        
        # Success message
        embed = discord.Embed(
            title="✅ Basic Tier Granted Successfully",
            description=(
                f"**User:** {user.display_name} (`{user.id}`)\n"
                f"**Tier:** {TIER_EMOJIS['basic']} Basic\n"
                f"**Duration:** {duration_text}\n"
                f"**Price:** $1/month equivalent\n"
            ),
            color=TIER_COLORS['basic']
        )
        
        if not permanent:
            embed.description += f"**Expires:** {expires_at.strftime('%Y-%m-%d %H:%M UTC')}\n"
        
        embed.add_field(
            name="🎯 Basic Tier Features",
            value=(
                f"• **Text Limit:** {limits['text_limit']} characters\n"
                f"• **Voice Limit:** {limits['voice_limit']//60} minutes\n"
                f"• **Daily Points:** {limits['daily_points_min']}-{limits['daily_points_max']}\n"
                f"• **Features:** Auto-translate, History"
            ),
            inline=False
        )
        
        if user.avatar:
            embed.set_thumbnail(url=user.avatar.url)
        
        embed.set_footer(text=f"Granted by {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Notify user
        try:
            user_embed = discord.Embed(
                title="🥉 Basic Tier Access Granted!",
                description=(
                    f"You've been granted **{duration_text}** of Basic tier access for Muse Translator!\n\n"
                    f"**Basic Tier Benefits:**\n"
                    f"• 📝 **500 character** text translations\n"
                    f"• 🎤 **60-minute** voice translations\n"
                    f"• 🔄 **Auto-translate** feature\n"
                    f"• 📚 **Translation history**\n"
                    f"• 💎 **10-15 daily points**\n"
                    f"• ⚡ **Standard support**\n\n"
                    f"💡 *Use `/status` to check your tier anytime!*"
                ),
                color=TIER_COLORS['basic']
            )
            
            if not permanent:
                user_embed.add_field(
                    name="⏰ Expiration",
                    value=expires_at.strftime('%B %d, %Y at %H:%M UTC'),
                    inline=False
                )
            
            await user.send(embed=user_embed)
            await interaction.followup.send("✅ User has been notified via DM", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("⚠️ Couldn't notify user (DMs disabled)", ephemeral=True)
        except Exception as dm_error:
            await interaction.followup.send(f"⚠️ Couldn't notify user: {dm_error}", ephemeral=True)
    
    except Exception as e:
        await interaction.response.send_message(f"❌ Error granting Basic tier: {str(e)}", ephemeral=True)

### ➖ **Remove Basic Tier**

@tree.command(name="removebasic", description="[ADMIN] Remove Basic tier access from any Discord user")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    user="Discord user to remove Basic tier from",
    reason="Reason for removal (optional)"
)
async def remove_basic(interaction: discord.Interaction, user: discord.User, reason: str = "Admin removal"):
    if interaction.user.id != YOUR_ADMIN_ID:
        await interaction.response.send_message("❌ Bot owner only!", ephemeral=True)
        return
    
    try:
        # Check if user has Basic tier
        if user.id not in tier_handler.basic_users:
            await interaction.response.send_message(
                f"❌ User {user.display_name} doesn't have Basic tier!",
                ephemeral=True
            )
            return
        
        # Remove from basic tier
        tier_handler.basic_users.discard(user.id)
        
        # Update database
        try:
            await db.update_user_premium(user.id, False, None)
        except Exception as db_error:
            print(f"Database update error: {db_error}")
        
        # Success message
        embed = discord.Embed(
            title="✅ Basic Tier Removed Successfully",
            description=(
                f"**User:** {user.display_name} (`{user.id}`)\n"
                f"**Previous Tier:** {TIER_EMOJIS['basic']} Basic\n"
                f"**New Tier:** {TIER_EMOJIS['free']} Free\n"
                f"**Reason:** {reason}\n"
            ),
            color=0xff6b6b
        )
        
        if user.avatar:
            embed.set_thumbnail(url=user.avatar.url)
        
        embed.set_footer(text=f"Removed by {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Notify user
        try:
            user_embed = discord.Embed(
                title="🥉 Basic Tier Access Removed",
                description=(
                    f"Your Basic tier access for Muse Translator has been removed.\n\n"
                    f"**Reason:** {reason}\n"
                    f"**Current Tier:** Free\n\n"
                    f"**Free Tier Limits:**\n"
                    f"• 📝 50 character text translations\n"
                    f"• 🎤 30-minute voice translations\n"
                    f"• 💎 5-10 daily points\n\n"
                    f"💡 *Use `/premium` to upgrade again!*"
                ),
                color=0xff6b6b
            )
            await user.send(embed=user_embed)
            await interaction.followup.send("✅ User has been notified via DM", ephemeral=True)
        except:
            await interaction.followup.send("⚠️ Couldn't notify user (DMs disabled)", ephemeral=True)
    
    except Exception as e:
        print(f"Error in remove_basic: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message(f"❌ Error removing Basic tier: {str(e)}", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ Error removing Basic tier: {str(e)}", ephemeral=True)

@tree.command(name="addpremium", description="[ADMIN] Grant Premium tier access to any Discord user", guild=discord.Object(id=YOUR_SERVER_ID))
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    user="Discord user to grant Premium tier to",
    days="Number of days of Premium access (default: 30)",
    permanent="Make this a permanent upgrade (default: False)"
)
async def add_premium(interaction: discord.Interaction, user: discord.User, days: int = 30, permanent: bool = False):
    if interaction.user.id != YOUR_ADMIN_ID:
        await interaction.response.send_message("❌ Bot owner only!", ephemeral=True)
        return
    
    if days <= 0 and not permanent:
        await interaction.response.send_message("❌ Days must be positive for temporary access!", ephemeral=True)
        return
    
    try:
        from datetime import datetime, timedelta
        
        if permanent:
            expires_at = None
            duration_text = "Permanent"
        else:
            expires_at = datetime.now() + timedelta(days=days)
            duration_text = f"{days} days"
        
        # Grant Premium tier
        await tier_handler.set_user_tier_async(user.id, 'premium', expires_at)
        
        # Get tier limits for display
        limits = tier_handler.get_limits_for_tier('premium')
        
        # Success message
        embed = discord.Embed(
            title="✅ Premium Tier Granted Successfully",
            description=(
                f"**User:** {user.display_name} (`{user.id}`)\n"
                f"**Tier:** {TIER_EMOJIS['premium']} Premium\n"
                f"**Duration:** {duration_text}\n"
                f"**Price:** $3/month equivalent\n"
            ),
            color=TIER_COLORS['premium']
        )
        
        if not permanent:
            embed.description += f"**Expires:** {expires_at.strftime('%Y-%m-%d %H:%M UTC')}\n"
        
        embed.add_field(
            name="🎯 Premium Tier Features",
            value=(
                f"• **Text Limit:** {limits['text_limit']:,} characters\n"
                f"• **Voice Limit:** {limits['voice_limit']//60} minutes\n"
                f"• **Daily Points:** {limits['daily_points_min']}-{limits['daily_points_max']}\n"
                f"• **Features:** Enhanced Voice, Priority Processing"
            ),
            inline=False
        )
        
        if user.avatar:
            embed.set_thumbnail(url=user.avatar.url)
        
        embed.set_footer(text=f"Granted by {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Notify user
        try:
            user_embed = discord.Embed(
                title="🥈 Premium Tier Access Granted!",
                description=(
                    f"You've been granted **{duration_text}** of Premium tier access for Muse Translator!\n\n"
                    f"**Premium Tier Benefits:**\n"
                    f"• 📝 **2,000 character** text translations\n"
                    f"• 🎤 **2-hour** voice translations\n"
                    f"• 🚀 **Enhanced voice features**\n"
                    f"• ⚡ **Priority processing**\n"
                    f"• 🔄 **Auto-translate** feature\n"
                    f"• 📚 **Translation history**\n"
                    f"• 💎 **15-20 daily points**\n"
                    f"• 🎯 **Priority support**\n\n"
                    f"💡 *Use `/voicechat2` for enhanced voice features!*"
                ),
                color=TIER_COLORS['premium']
            )
            
            if not permanent:
                user_embed.add_field(
                    name="⏰ Expiration",
                    value=expires_at.strftime('%B %d, %Y at %H:%M UTC'),
                    inline=False
                )
            
            await user.send(embed=user_embed)
            await interaction.followup.send("✅ User has been notified via DM", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("⚠️ Couldn't notify user (DMs disabled)", ephemeral=True)
        except Exception as dm_error:
            await interaction.followup.send(f"⚠️ Couldn't notify user: {dm_error}", ephemeral=True)
    
    except Exception as e:
        await interaction.response.send_message(f"❌ Error granting Premium tier: {str(e)}", ephemeral=True)

### ➖ **Remove Premium Tier**

@tree.command(name="removepremium", description="[ADMIN] Remove Premium tier access from any Discord user")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    user="Discord user to remove Premium tier from",
    reason="Reason for removal (optional)"
)
async def remove_premium(interaction: discord.Interaction, user: discord.User, reason: str = "Admin removal"):
    if interaction.user.id != YOUR_ADMIN_ID:
        await interaction.response.send_message("❌ Bot owner only!", ephemeral=True)
        return
    
    try:
        # Check if user has Premium tier
        if user.id not in tier_handler.premium_users:
            await interaction.response.send_message(
                f"❌ User {user.display_name} doesn't have Premium tier!",
                ephemeral=True
            )
            return
        
        # Remove from premium tier
        tier_handler.premium_users.discard(user.id)
        
        # Update database
        try:
            await db.update_user_premium(user.id, False, None)
        except Exception as db_error:
            print(f"Database update error: {db_error}")
        
        # Success message
        embed = discord.Embed(
            title="✅ Premium Tier Removed Successfully",
            description=(
                f"**User:** {user.display_name} (`{user.id}`)\n"
                f"**Previous Tier:** {TIER_EMOJIS['premium']} Premium\n"
                f"**New Tier:** {TIER_EMOJIS['free']} Free\n"
                f"**Reason:** {reason}\n"
            ),
            color=0xff6b6b
        )
        
        if user.avatar:
            embed.set_thumbnail(url=user.avatar.url)
        
        embed.set_footer(text=f"Removed by {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Notify user
        try:
            user_embed = discord.Embed(
                title="🥈 Premium Tier Access Removed",
                description=(
                    f"Your Premium tier access for Muse Translator has been removed.\n\n"
                    f"**Reason:** {reason}\n"
                    f"**Current Tier:** Free\n\n"
                    f"**Free Tier Limits:**\n"
                    f"• 📝 50 character text translations\n"
                    f"• 🎤 30-minute voice translations\n"
                    f"• 💎 5-10 daily points\n\n"
                    f"💡 *Use `/premium` to upgrade again!*"
                ),
                color=0xff6b6b
            )
            await user.send(embed=user_embed)
            await interaction.followup.send("✅ User has been notified via DM", ephemeral=True)
        except:
            await interaction.followup.send("⚠️ Couldn't notify user (DMs disabled)", ephemeral=True)
    
    except Exception as e:
        print(f"Error in remove_premium: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message(f"❌ Error removing Premium tier: {str(e)}", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ Error removing Premium tier: {str(e)}", ephemeral=True)

@tree.command(name="addpro", description="[ADMIN] Grant Pro tier access to any Discord user", guild=discord.Object(id=YOUR_SERVER_ID))
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    user="Discord user to grant Pro tier to",
    days="Number of days of Pro access (default: 30)",
    permanent="Make this a permanent upgrade (default: False)"
)
async def add_pro(interaction: discord.Interaction, user: discord.User, days: int = 30, permanent: bool = False):
    if interaction.user.id != YOUR_ADMIN_ID:
        await interaction.response.send_message("❌ Bot owner only!", ephemeral=True)
        return
    
    if days <= 0 and not permanent:
        await interaction.response.send_message("❌ Days must be positive for temporary access!", ephemeral=True)
        return
    
    try:
        from datetime import datetime, timedelta
        
        if permanent:
            expires_at = None
            duration_text = "Permanent"
        else:
            expires_at = datetime.now() + timedelta(days=days)
            duration_text = f"{days} days"
        
        # Grant Pro tier
        await tier_handler.set_user_tier_async(user.id, 'pro', expires_at)
        
        # Get tier limits for display
        limits = tier_handler.get_limits_for_tier('pro')
        
        # Success message
        embed = discord.Embed(
            title="✅ Pro Tier Granted Successfully",
            description=(
                f"**User:** {user.display_name} (`{user.id}`)\n"
                f"**Tier:** {TIER_EMOJIS['pro']} Pro\n"
                f"**Duration:** {duration_text}\n"
                f"**Price:** $5/month equivalent\n"
            ),
            color=TIER_COLORS['pro']
        )
        
        if not permanent:
            embed.description += f"**Expires:** {expires_at.strftime('%Y-%m-%d %H:%M UTC')}\n"
        
        embed.add_field(
            name="🎯 Pro Tier Features",
            value=(
                f"• **Text Limit:** Unlimited\n"
                f"• **Voice Limit:** Unlimited\n"
                f"• **Daily Points:** {limits['daily_points_min']}-{limits['daily_points_max']}\n"
                f"• **Features:** All Features + Beta Access"
            ),
            inline=False
        )
        
        if user.avatar:
            embed.set_thumbnail(url=user.avatar.url)
        
        embed.set_footer(text=f"Granted by {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Notify user
        try:
            user_embed = discord.Embed(
                title="🥇 Pro Tier Access Granted!",
                description=(
                    f"You've been granted **{duration_text}** of Pro tier access for Muse Translator!\n\n"
                    f"**Pro Tier Benefits:**\n"
                    f"• 📝 **Unlimited** text translations\n"
                    f"• 🎤 **Unlimited** voice translations\n"
                    f"• 🚀 **All enhanced features**\n"
                    f"• 🧪 **Beta access** to new features\n"
                    f"• ⚡ **Priority processing**\n"
                    f"• 🔄 **Custom integrations**\n"
                    f"• 📚 **Full translation history**\n"
                    f"• 💎 **20-25 daily points**\n"
                    f"• 👑 **Priority support**\n\n"
                    f"💡 *You now have access to all current and future features!*"
                ),
                color=TIER_COLORS['pro']
            )
            
            if not permanent:
                user_embed.add_field(
                    name="⏰ Expiration",
                    value=expires_at.strftime('%B %d, %Y at %H:%M UTC'),
                    inline=False
                )
            
            await user.send(embed=user_embed)
            await interaction.followup.send("✅ User has been notified via DM", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("⚠️ Couldn't notify user (DMs disabled)", ephemeral=True)
        except Exception as dm_error:
            await interaction.followup.send(f"⚠️ Couldn't notify user: {dm_error}", ephemeral=True)
    
    except Exception as e:
        await interaction.response.send_message(f"❌ Error granting Pro tier: {str(e)}", ephemeral=True)

### ➖ **Remove Pro Tier**

@tree.command(name="removepro", description="[ADMIN] Remove Pro tier access from any Discord user")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    user="Discord user to remove Pro tier from",
    reason="Reason for removal (optional)"
)
async def remove_pro(interaction: discord.Interaction, user: discord.User, reason: str = "Admin removal"):
    if interaction.user.id != YOUR_ADMIN_ID:
        await interaction.response.send_message("❌ Bot owner only!", ephemeral=True)
        return
    
    try:
        # Check if user has Pro tier
        if user.id not in tier_handler.pro_users:
            await interaction.response.send_message(
                f"❌ User {user.display_name} doesn't have Pro tier!",
                ephemeral=True
            )
            return
        
        # Remove from pro tier
        tier_handler.pro_users.discard(user.id)
        
        # Update database
        try:
            await db.update_user_premium(user.id, False, None)
        except Exception as db_error:
            print(f"Database update error: {db_error}")
        
        # Success message
        embed = discord.Embed(
            title="✅ Pro Tier Removed Successfully",
            description=(
                f"**User:** {user.display_name} (`{user.id}`)\n"
                f"**Previous Tier:** {TIER_EMOJIS['pro']} Pro\n"
                f"**New Tier:** {TIER_EMOJIS['free']} Free\n"
                f"**Reason:** {reason}\n"
            ),
            color=0xff6b6b
        )
        
        if user.avatar:
            embed.set_thumbnail(url=user.avatar.url)
        
        embed.set_footer(text=f"Removed by {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Notify user
        try:
            user_embed = discord.Embed(
                title="🥇 Pro Tier Access Removed",
                description=(
                    f"Your Pro tier access for Muse Translator has been removed.\n\n"
                    f"**Reason:** {reason}\n"
                    f"**Current Tier:** Free\n\n"
                    f"**Free Tier Limits:**\n"
                    f"• 📝 50 character text translations\n"
                    f"• 🎤 30-minute voice translations\n"
                    f"• 💎 5-10 daily points\n\n"
                    f"💡 *Use `/premium` to upgrade again!*"
                ),
                color=0xff6b6b
            )
            await user.send(embed=user_embed)
            await interaction.followup.send("✅ User has been notified via DM", ephemeral=True)
        except:
            await interaction.followup.send("⚠️ Couldn't notify user (DMs disabled)", ephemeral=True)
    
    except Exception as e:
        print(f"Error in remove_pro: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message(f"❌ Error removing Pro tier: {str(e)}", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ Error removing Pro tier: {str(e)}", ephemeral=True)

# Bonus: Add a command to check what tier a user has
@tree.command(name="checktier", description="[ADMIN] Check what tier a user currently has")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(user="Discord user to check tier for")
async def check_tier(interaction: discord.Interaction, user: discord.User):
    if interaction.user.id != YOUR_ADMIN_ID:
        await interaction.response.send_message("❌ Bot owner only!", ephemeral=True)
        return
    
    # Check user's current tier
    if user.id in tier_handler.pro_users:
        current_tier = "Pro"
        emoji = TIER_EMOJIS['pro']
        color = 0x9b59b6
    elif user.id in tier_handler.premium_users:
        current_tier = "Premium"
        emoji = TIER_EMOJIS['premium']
        color = 0xf39c12
    elif user.id in tier_handler.basic_users:
        current_tier = "Basic"
        emoji = TIER_EMOJIS['basic']
        color = 0x3498db
    else:
        current_tier = "Free"
        emoji = TIER_EMOJIS['free']
        color = 0x95a5a6
    
    embed = discord.Embed(
        title=f"🔍 Tier Check: {user.display_name}",
        description=f"**Current Tier:** {emoji} {current_tier}",
        color=color
    )
    
    if user.avatar:
        embed.set_thumbnail(url=user.avatar.url)
    
    embed.add_field(name="User ID", value=f"`{user.id}`", inline=True)
    embed.set_footer(text=f"Checked by {interaction.user.display_name}")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

### 📈 **Tier Statistics**

@tree.command(name="tierstats", description="[ADMIN] View tier distribution statistics")
@app_commands.default_permissions(administrator=True)
async def tier_stats(interaction: discord.Interaction):
    if interaction.user.id != YOUR_ADMIN_ID:
        await interaction.response.send_message("❌ Bot owner only!", ephemeral=True)
        return
    
    try:
        # Get tier counts directly from the sets
        basic_count = len(tier_handler.basic_users)
        premium_count = len(tier_handler.premium_users)
        pro_count = len(tier_handler.pro_users)
        
        # Calculate totals
        total_premium = basic_count + premium_count + pro_count
        
        # Get database stats if available
        try:
            # Try to get total registered users from database
            async with aiosqlite.connect(db.db_path) as database:
                async with database.execute("SELECT COUNT(*) FROM users") as cursor:
                    result = await cursor.fetchone()
                    total_users = result[0] if result else 0
        except:
            total_users = total_premium  # Fallback if database query fails
        
        free_users = max(0, total_users - total_premium)
        
        # Create statistics embed
        embed = discord.Embed(
            title="📈 Tier Distribution Statistics",
            description="Current tier membership breakdown",
            color=0x3498db
        )
        
        # Add tier counts with percentages
        if total_users > 0:
            basic_percent = (basic_count / total_users) * 100
            premium_percent = (premium_count / total_users) * 100
            pro_percent = (pro_count / total_users) * 100
            free_percent = (free_users / total_users) * 100
        else:
            basic_percent = premium_percent = pro_percent = free_percent = 0
        
        embed.add_field(
            name=f"{TIER_EMOJIS['free']} Free Tier",
            value=f"**{free_users}** users ({free_percent:.1f}%)",
            inline=True
        )
        
        embed.add_field(
            name=f"{TIER_EMOJIS['basic']} Basic Tier",
            value=f"**{basic_count}** users ({basic_percent:.1f}%)",
            inline=True
        )
        
        embed.add_field(
            name=f"{TIER_EMOJIS['premium']} Premium Tier",
            value=f"**{premium_count}** users ({premium_percent:.1f}%)",
            inline=True
        )
        
        embed.add_field(
            name=f"{TIER_EMOJIS['pro']} Pro Tier",
            value=f"**{pro_count}** users ({pro_percent:.1f}%)",
            inline=True
        )
        
        # Total users
        embed.add_field(
            name="👥 Total Users",
            value=f"**{total_users}** registered",
            inline=True
        )
        
        # Total premium users
        embed.add_field(
            name="💎 Total Premium Users",
            value=f"**{total_premium}** users",
            inline=True
        )
        
        # Revenue estimation
        estimated_revenue = (basic_count * 1) + (premium_count * 3) + (pro_count * 5)
        embed.add_field(
            name="💰 Estimated Monthly Revenue",
            value=f"**${estimated_revenue}** USD",
            inline=False
        )
        
        # Conversion rate
        if total_users > 0:
            conversion_rate = (total_premium / total_users) * 100
            embed.add_field(
                name="📊 Premium Conversion Rate",
                value=f"**{conversion_rate:.1f}%**",
                inline=True
            )
        
        # Add visual progress bar for premium users
        if total_users > 0:
            premium_ratio = total_premium / total_users
            bar_length = 20
            filled_length = int(bar_length * premium_ratio)
            bar = "█" * filled_length + "░" * (bar_length - filled_length)
            embed.add_field(
                name="📈 Premium User Distribution",
                value=f"`{bar}` {premium_ratio:.1%}",
                inline=False
            )
        
        embed.set_footer(text=f"Generated by {interaction.user.display_name} • Last updated")
        embed.timestamp = discord.utils.utcnow()
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    except Exception as e:
        print(f"Tier stats error: {e}")
        await interaction.response.send_message(f"❌ Error getting tier stats: {str(e)}", ephemeral=True)


### 🧹 **Cleanup Expired Tiers**

@tree.command(name="cleanupexpired", description="[ADMIN] Clean up expired tier memberships")
@app_commands.default_permissions(administrator=True)
async def cleanup_expired(interaction: discord.Interaction):
    if interaction.user.id != YOUR_ADMIN_ID:
        await interaction.response.send_message("❌ Bot owner only!", ephemeral=True)
        return
    
    try:
        await interaction.response.defer(ephemeral=True)
        
        expired_users = []
        current_time = datetime.now()
        
        # Check database for expired premium subscriptions
        try:
            async with aiosqlite.connect(db.db_path) as database:
                # Get users with expired premium status
                async with database.execute('''
                    SELECT user_id, premium_expires, username 
                    FROM users 
                    WHERE is_premium = TRUE 
                    AND premium_expires IS NOT NULL 
                    AND premium_expires < ?
                ''', (current_time.isoformat(),)) as cursor:
                    expired_db_users = await cursor.fetchall()
                
                # Process expired users
                for user_id, expires_at, username in expired_db_users:
                    user_tier = None
                    
                    # Determine which tier they had and remove them
                    if user_id in tier_handler.pro_users:
                        tier_handler.pro_users.discard(user_id)
                        user_tier = 'pro'
                    elif user_id in tier_handler.premium_users:
                        tier_handler.premium_users.discard(user_id)
                        user_tier = 'premium'
                    elif user_id in tier_handler.basic_users:
                        tier_handler.basic_users.discard(user_id)
                        user_tier = 'basic'
                    
                    if user_tier:
                        expired_users.append((user_id, user_tier, username, expires_at))
                
                # Update database - set expired users to non-premium
                if expired_db_users:
                    user_ids = [str(user[0]) for user in expired_db_users]
                    placeholders = ','.join(['?' for _ in user_ids])
                    await database.execute(f'''
                        UPDATE users 
                        SET is_premium = FALSE, premium_expires = NULL 
                        WHERE user_id IN ({placeholders})
                    ''', user_ids)
                    await database.commit()
        
        except Exception as db_error:
            print(f"Database cleanup error: {db_error}")
            # Continue with manual cleanup if database fails
        
        # Manual cleanup for users without database entries
        # (This is a fallback - you might want to implement expiration tracking)
        manual_expired = 0
        
        # If you have any manual expiration logic, add it here
        # For now, we'll just report database cleanup results
        
        if not expired_users and manual_expired == 0:
            embed = discord.Embed(
                title="✅ Cleanup Complete",
                description="No expired tier memberships found.",
                color=0x2ecc71
            )
        else:
            # Create summary of cleaned up users
            total_cleaned = len(expired_users) + manual_expired
            embed = discord.Embed(
                title="🧹 Cleanup Complete",
                description=f"Cleaned up **{total_cleaned}** expired tier memberships:",
                color=0xf39c12
            )
            
            # Group by tier
            basic_expired = [u for u in expired_users if u[1] == 'basic']
            premium_expired = [u for u in expired_users if u[1] == 'premium']
            pro_expired = [u for u in expired_users if u[1] == 'pro']
            
            if basic_expired:
                embed.add_field(
                    name=f"{TIER_EMOJIS['basic']} Basic Expired",
                    value=f"**{len(basic_expired)}** users",
                    inline=True
                )
            
            if premium_expired:
                embed.add_field(
                    name=f"{TIER_EMOJIS['premium']} Premium Expired",
                    value=f"**{len(premium_expired)}** users",
                    inline=True
                )
            
            if pro_expired:
                embed.add_field(
                    name=f"{TIER_EMOJIS['pro']} Pro Expired",
                    value=f"**{len(pro_expired)}** users",
                    inline=True
                )
            
            # Add details of expired users (limit to prevent embed overflow)
            if expired_users:
                details = []
                for user_id, tier, username, expires_at in expired_users[:10]:  # Limit to 10
                    tier_emoji = TIER_EMOJIS.get(tier, '❓')
                    details.append(f"{tier_emoji} {username or f'User {user_id}'} (expired: {expires_at[:10]})")
                
                if len(expired_users) > 10:
                    details.append(f"... and {len(expired_users) - 10} more")
                
                embed.add_field(
                    name="📋 Expired Users Details",
                    value="\n".join(details) if details else "None",
                    inline=False
                )
        
        embed.set_footer(text=f"Cleanup performed by {interaction.user.display_name}")
        embed.timestamp = discord.utils.utcnow()
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        
        # Optional: Notify expired users
        if expired_users:
            notification_count = 0
            for user_id, tier, username, expires_at in expired_users:
                try:
                    user = await client.fetch_user(user_id)
                    if user:
                        tier_name = tier.title()
                        tier_emoji = TIER_EMOJIS.get(tier, '❓')
                        
                        notify_embed = discord.Embed(
                            title=f"{tier_emoji} {tier_name} Tier Expired",
                            description=(
                                f"Your {tier_name} tier access for Muse Translator has expired.\n\n"
                                f"**Expired on:** {expires_at[:10]}\n"
                                f"**Current Tier:** Free\n\n"
                                f"**Free Tier Limits:**\n"
                                f"• 📝 50 character text translations\n"
                                f"• 🎤 30-minute voice translations\n"
                                f"• 💎 5-10 daily points\n\n"
                                f"💡 *Use `/premium` to renew your subscription!*"
                            ),
                            color=0xff6b6b
                        )
                        
                        await user.send(embed=notify_embed)
                        notification_count += 1
                except:
                    continue  # Skip if can't notify user
            
            if notification_count > 0:
                await interaction.followup.send(
                    f"✅ Notified {notification_count} users about their expired subscriptions",
                    ephemeral=True
                )
    
    except Exception as e:
        print(f"Cleanup error: {e}")
        if not interaction.response.is_done():
            await interaction.response.send_message(f"❌ Error during cleanup: {str(e)}", ephemeral=True)
        else:
            await interaction.followup.send(f"❌ Error during cleanup: {str(e)}", ephemeral=True)

@tree.command(name="grantpoints", description="[ADMIN] Grant points to any Discord user", guild=discord.Object(id=YOUR_SERVER_ID))
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    user="Discord user to grant points to",
    points="Number of points to grant",
    reason="Reason for granting points (optional)"
)
async def grant_points(interaction: discord.Interaction, user: discord.User, points: int, reason: str = "Admin grant"):
    # Double security: Must be admin in YOUR server AND be you
    if interaction.user.id != YOUR_ADMIN_ID:
        await interaction.response.send_message("❌ Bot owner only!", ephemeral=True)
        return
    
    if points <= 0:
        await interaction.response.send_message("❌ Points must be positive!", ephemeral=True)
        return
    
    try:
        # Get user data
        user_data = reward_db.get_or_create_user(user.id, user.display_name)
        old_points = user_data['points']
        
        # Grant points
        reward_db.add_points(user.id, points, f"Admin grant: {reason}")
        new_points = old_points + points
        
        # Success message
        embed = discord.Embed(
            title="✅ Points Granted Successfully",
            description=(
                f"**User:** {user.display_name} (`{user.id}`)\n"
                f"**Points Granted:** +{points:,}\n"
                f"**Previous Balance:** {old_points:,}\n"
                f"**New Balance:** {new_points:,}\n"
                f"**Reason:** {reason}"
            ),
            color=0x00ff00
        )
        
        if user.avatar:
            embed.set_thumbnail(url=user.avatar.url)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Try to notify the user
        try:
            user_embed = discord.Embed(
                title="💎 Points Granted!",
                description=(
                    f"You've been granted **{points:,} points** for Muse Translator!\n\n"
                    f"**Reason:** {reason}\n"
                    f"**New Balance:** {new_points:,} points\n\n"
                    f"💡 *Use `/shop` to spend your points!*"
                ),
                color=0x00ff00
            )
            await user.send(embed=user_embed)
            
            await interaction.followup.send("✅ User has been notified via DM", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("⚠️ Couldn't notify user (DMs disabled)", ephemeral=True)
        except Exception as dm_error:
            await interaction.followup.send(f"⚠️ Couldn't notify user: {dm_error}", ephemeral=True)
    
    except Exception as e:
        await interaction.response.send_message(f"❌ Error granting points: {str(e)}", ephemeral=True)

@tree.command(name="removepoints", description="[ADMIN] Remove points from any Discord user", guild=discord.Object(id=YOUR_SERVER_ID))
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    user="Discord user to remove points from",
    points="Number of points to remove",
    reason="Reason for removing points (optional)"
)
async def remove_points(interaction: discord.Interaction, user: discord.User, points: int, reason: str = "Admin removal"):
    # Double security: Must be admin in YOUR server AND be you
    if interaction.user.id != YOUR_ADMIN_ID:
        await interaction.response.send_message("❌ Bot owner only!", ephemeral=True)
        return
    
    if points <= 0:
        await interaction.response.send_message("❌ Points must be positive!", ephemeral=True)
        return
    
    try:
        # Get user data
        user_data = reward_db.get_or_create_user(user.id, user.display_name)
        old_points = user_data['points']
        
        if old_points < points:
            await interaction.response.send_message(
                f"❌ User only has {old_points:,} points, cannot remove {points:,}!",
                ephemeral=True
            )
            return
        
        # Remove points
        reward_db.add_points(user.id, -points, f"Admin removal: {reason}")
        new_points = old_points - points
        
        # Success message
        embed = discord.Embed(
            title="✅ Points Removed Successfully",
            description=(
                f"**User:** {user.display_name} (`{user.id}`)\n"
                f"**Points Removed:** -{points:,}\n"
                f"**Previous Balance:** {old_points:,}\n"
                f"**New Balance:** {new_points:,}\n"
                f"**Reason:** {reason}"
            ),
            color=0xff6b6b
        )
        
        if user.avatar:
            embed.set_thumbnail(url=user.avatar.url)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Try to notify the user
        try:
            user_embed = discord.Embed(
                title="💎 Points Deducted",
                description=(
                    f"**{points:,} points** have been deducted from your Muse Translator account.\n\n"
                    f"**Reason:** {reason}\n"
                    f"**New Balance:** {new_points:,} points\n\n"
                    f"💡 *Earn more points with `/daily` and regular usage!*"
                ),
                color=0xff6b6b
            )
            await user.send(embed=user_embed)
            
            await interaction.followup.send("✅ User has been notified via DM", ephemeral=True)
        except discord.Forbidden:
            await interaction.followup.send("⚠️ Couldn't notify user (DMs disabled)", ephemeral=True)
        except Exception as dm_error:
            await interaction.followup.send(f"⚠️ Couldn't notify user: {dm_error}", ephemeral=True)
    
    except Exception as e:
        await interaction.response.send_message(f"❌ Error removing points: {str(e)}", ephemeral=True)


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

@tree.command(name="forceachievement", description="Force trigger achievement check (owner only)", guild=discord.Object(id=YOUR_SERVER_ID))
@app_commands.default_permissions(administrator=True)
async def force_achievement_check(interaction: discord.Interaction):
    if interaction.user.id != 1192196672437096520:  # Your user ID
        await interaction.response.send_message("❌ Owner only!", ephemeral=True)
        return
    
    await interaction.response.send_message("🔄 Forcing achievement check...", ephemeral=True)
    
    try:
        new_achievements = await safe_check_and_award_achievements(
            interaction.user.id, 
            interaction.user.display_name,
            'manual_test'
        )
        
        if new_achievements:
            await interaction.followup.send(
                f"✅ Found {len(new_achievements)} new achievements!",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                "ℹ️ No new achievements found.",
                ephemeral=True
            )
            
    except Exception as e:
        logger.error(f"Force achievement check error: {e}")
        await interaction.followup.send(
            f"❌ Error: {str(e)}",
            ephemeral=True
        )

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
        # NOW add the streak column
        await setup_streak_column()
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
# NEW: Background task to clean up expired rewards
async def cleanup_expired_rewards():
    F"Background task to clean up expired rewards"""
    while True:
        try:
            reward_db.cleanup_expired_rewards()
            logger.info("Cleaned up expired rewards")
        except Exception as e:
            logger.error(f"Error cleaning up expired rewards: {e}")
        
        # Run cleanup every hour
        await asyncio.sleep(3600)
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
# In your main bot startup function
async def setup_hook():
    # Your existing setup code...
    
    # Load translations
    load_translations()
    print(f"Loaded translations for: {', '.join(SUPPORTED_UI_LANGUAGES)}")

def safe_db_operation(operation, *args, **kwargs):
    """Safely execute database operations with error handling"""
    try:
        return operation(*args, **kwargs)
    except Exception as e:
        logger.error(f"Database operation failed: {e}")
        return None

if 'HOSTING' in os.environ:
    # Install dependencies when deploying to cloud
    system('pip install -r requirements.txt')

if __name__ == "__main__":
    try:
        print("🗄️ Initializing reward database...")
        reward_db.initialize_database()
        print("✅ Database initialized successfully!")
    except Exception as e:
        print(f"Database initialization error: {e}")
    
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
