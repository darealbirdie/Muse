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
from typing import Dict, Optional
from dotenv import load_dotenv
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
from achievement_system import achievement_db, get_rank_from_points, send_achievement_notification, ACHIEVEMENTS, RARITY_INFO
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

YOUR_ADMIN_ID = 1192196672437096520
YOUR_SERVER_ID = 1332522833326375022
# Tier colors for embeds
TIER_COLORS = {
    'free': 0x95a5a6,
    'basic': 0xcd7f32,
    'premium': 0xc0c0c0,
    'pro': 0xffd700
}

TIER_EMOJIS = {
    'free': '🆓',
    'basic': '🥉',
    'premium': '🥈',
    'pro': '🥇'
}

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
class TierHandler:
    def __init__(self):
        self.premium_users = set()  # Premium users
        self.pro_users = set()      # Pro users  
        self.basic_users = set()    # Basic users
        self.user_tiers = {}        # Store user tier info with expiration
        self.usage_tracking = {}    # Track daily usage per user
        self.tiers = {
            'free': {
                'text_limit': 100,    # 100 characters per translation
                'voice_limit': 1800,  # 30 minutes in seconds
                'daily_points_min': 5,
                'daily_points_max': 10,
                'daily_translations': 50,
                'features': ['basic_translation', 'voice_chat']
            },
            'basic': {
                'text_limit': 500,    # 500 characters per translation
                'voice_limit': 3600,  # 60 minutes in seconds
                'daily_points_min': 10,
                'daily_points_max': 15,
                'daily_translations': 150,
                'features': ['basic_translation', 'voice_chat', 'auto_translate']
            },
            'premium': {
                'text_limit': 2000,   # 2000 characters per translation
                'voice_limit': 7200,  # 2 hours in seconds
                'daily_points_min': 15,
                'daily_points_max': 20,
                'daily_translations': 500,
                'features': ['basic_translation', 'voice_chat', 'auto_translate', 'enhanced_voice', 'priority_support']
            },
            'pro': {
                'text_limit': float('inf'),  # Unlimited characters
                'voice_limit': float('inf'), # Unlimited voice translation
                'daily_points_min': 25,
                'daily_points_max': 35,
                'daily_translations': float('inf'),
                'features': ['all_features', 'priority_processing', 'custom_models']
            }
        }
    
    # ORIGINAL METHODS (from your working code)
    def get_limits(self, user_id: int):
        """Get limits for a specific user"""
        tier = self.get_user_tier(user_id)
        return self.tiers.get(tier, self.tiers['free'])
    
    def get_limits_for_tier(self, tier_name: str):
        """Get limits for a specific tier by name"""
        return self.tiers.get(tier_name, self.tiers['free'])
    
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
    
    # ADDITIONAL METHODS (new functionality)
    def check_usage_limits(self, user_id: int, usage_type: str, amount: int = 1):
        """Check if user can perform an action based on their tier limits"""
        from datetime import datetime, date
        
        tier = self.get_user_tier(user_id)
        limits = self.tiers[tier]
        
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
        if usage_type == 'translation':
            if daily_usage['translations'] + amount > limits['daily_translations']:
                return False, f"Daily translation limit reached ({limits['daily_translations']})"
        
        elif usage_type == 'text_characters':
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
                limit_key = f'daily_{key}' if key != 'voice_seconds' else 'voice_limit'
                remaining[key] = max(0, limits[limit_key] - usage.get(key, 0))
        
        remaining['text_limit'] = limits['text_limit']
        return remaining
    
    def has_feature(self, user_id: int, feature: str):
        """Check if user has access to a specific feature"""
        tier = self.get_user_tier(user_id)
        features = self.tiers[tier].get('features', [])
        return feature in features or 'all_features' in features
    
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
            'pro': 10.0      # $10/month
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

@tree.command(name="start", description="Initialize your personal translation bot")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def start(interaction: discord.Interaction):
    await track_command_usage(interaction)  # Track usage for points
    
    user_id = interaction.user.id
    guild_id = interaction.guild_id
    
    # Initialize user in reward system
    user_data = reward_db.get_or_create_user(user_id, interaction.user.display_name)
    is_new_user = user_data['total_sessions'] == 0
    
    # Handle guild-based translator initialization
    if guild_id:
        if guild_id not in translation_server.translators:
            translation_server.translators[guild_id] = {}
        
        if user_id not in translation_server.translators[guild_id]:
            translation_server.translators[guild_id][user_id] = {}
            translation_server.get_user_url(user_id)
    
    # Get current tier for display
    current_tier = await tier_handler.get_user_tier_async(user_id)
    tier_info = tier_handler.get_tier_info(current_tier)
    limits = await tier_handler.get_limits_async(user_id)
    
    if is_new_user:
        # Create new user welcome embed
        embed = discord.Embed(
            title=f"🎉 Welcome to Muse Translator! {tier_info['emoji']}",
            description=f"Hello {interaction.user.display_name}! Your personal translator is ready to use.",
            color=0x2ecc71
        )
        
        # Add tier status for new users
        embed.add_field(
            name=f"⭐ Your Tier: {tier_info['name']}",
            value=(
                f"📝 Text Limit: {limits['text_limit'] if limits['text_limit'] != float('inf') else 'Unlimited'} chars\n"
                f"🎤 Voice Limit: {limits['voice_limit']//60 if limits['voice_limit'] != float('inf') else 'Unlimited'} min\n"
                f"💎 Points: {user_data['points']:,}"
            ),
            inline=False
        )
        
        # Getting started tips for new users
        embed.add_field(
            name="🚀 Getting Started",
            value=(
                "• Use `/daily` to claim daily points\n"
                "• Try `/texttr` for your first translation\n"
                "• Check `/shop` for temporary upgrades\n"
                "• Use `/help` for detailed commands"
            ),
            inline=False
        )
        
    else:
        # Returning user embed
        embed = discord.Embed(
            title=f"🚀 Welcome Back to Muse! {tier_info['emoji']}",
            description=f"Hello {interaction.user.display_name}! Your translator is ready to use.",
            color=tier_info['color']
        )
        
        # Show user stats
        embed.add_field(
            name="📊 Your Stats",
            value=(
                f"💎 Points: {user_data['points']:,}\n"
                f"🎯 Sessions: {user_data['total_sessions']}\n"
                f"⏱️ Usage: {user_data['total_usage_hours']:.1f}h\n"
                f"⭐ Tier: {tier_info['name']}"
            ),
            inline=True
        )
        
        # Daily reward reminder
        from datetime import datetime
        today = datetime.now().date().isoformat()
        if user_data['last_daily_claim'] != today:
            embed.add_field(
                name="🎁 Daily Reward Available",
                value="Use `/daily` to claim your points!",
                inline=True
            )
        else:
            embed.add_field(
                name="✅ Daily Claimed",
                value="Come back tomorrow for more points!",
                inline=True
            )
    
    # Add command categories (same for both new and returning users)
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
    
    # Reward system commands
    embed.add_field(
        name="💎 Points & Rewards",
        value=(
            "`/daily` - Claim daily points\n"
            "`/shop` - Browse point shop\n"
            "`/profile` - View your profile\n"
            "`/leaderboard` - See top users"
            "`/transactions` - View point transaction history\n"
        ),
        inline=False
    )
    
    embed.add_field(
        name="⚙️ Settings & Info",
        value=(
            "`/hide` or `/show` - Toggle original text visibility\n"
            "`/history` - View translation history\n"
            "`/list` - See all supported languages\n"
            "`/upgrade` - Unlock premium features\n"
            "`/help` - Full command list\n"
            "`/stop` - End translation session"
        ),
        inline=False
    )
    
    # Add feedback & community section
    embed.add_field(
        name="💬 Feedback & Community",
        value=(
            "`/feedback` - Rate and review Muse (earn points!)\n"
            "`/reviews` - See what other users are saying\n"
            "`/invite` - Share Muse with friends"
        ),
        inline=False
    )
    
    # Add tier-specific information
    if current_tier == 'free':
        embed.add_field(
            name="💡 Upgrade Benefits",
            value=(
                "🥉 **Basic ($1/month):** 500 chars, 1h voice, history access\n"
                "🥈 **Premium ($3/month):** 2000 chars, 2h voice, priority processing\n"
                "🥇 **Pro ($5/month):** Unlimited everything + beta features"
            ),
            inline=False
        )
    else:
        embed.add_field(
            name="🎉 Premium Features Active",
            value=(
                f"• Enhanced limits: {limits['text_limit'] if limits['text_limit'] != float('inf') else 'Unlimited'} chars\n"
                f"• Voice time: {limits['voice_limit']//60 if limits['voice_limit'] != float('inf') else 'Unlimited'} minutes\n"
                f"• Point multiplier: {tier_info.get('point_multiplier', '1x')}\n"
                "• Thank you for supporting Muse! 💖"
            ),
            inline=False
        )
    
    # Add language format help
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
    
    # Context-specific footer
    if interaction.guild:
        embed.set_footer(text=f"Server Mode: {interaction.guild.name} | Join our support server: discord.gg/VMpBsbhrff")
    else:
        embed.set_footer(text="User Mode: Perfect for DMs | Join our support server: discord.gg/VMpBsbhrff")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)
    
    # Log the initialization
    logger.info(f"🔥 User {'initialized' if is_new_user else 'returned'}: {interaction.user.display_name} (ID: {user_id}) - Tier: {current_tier}, Points: {user_data['points']}")

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
    try:
        # Track command usage safely
        try:
            await track_command_usage(interaction)
        except Exception as e:
            logger.error(f"Failed to track command usage: {e}")
        
        user_id = interaction.user.id
        username = interaction.user.display_name
        
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
        
        # Check if user is premium (memory first, then database)
        is_premium = user_id in tier_handler.premium_users
        if not is_premium:
            try:
                user_data = await db.get_or_create_user(user_id, username)
                if user_data and user_data.get('is_premium', False):
                    is_premium = True
                    tier_handler.premium_users.add(user_id)  # Cache for future
            except Exception as e:
                logger.error(f"Failed to check premium status from database: {e}")
        
        # Get limits based on premium status
        if is_premium:
            text_limit = float('inf')
        else:
            text_limit = 150  # Free tier limit
        
        # Check text length
        if len(text) > text_limit:
            await interaction.response.send_message(
                f"🔒 Text too long! Free tier limit: {text_limit} characters\n"
                f"💡 Use `/upgrade` to get unlimited translation!",
                ephemeral=True
            )
            return
        
        # Handle guild context check
        if interaction.guild:
            guild_id = interaction.guild_id
            if (guild_id not in translation_server.translators or 
                user_id not in translation_server.translators[guild_id]):
                await interaction.response.send_message(
                    "Please use /start first to initialize your translator! 🎯", 
                    ephemeral=True
                )
                return
        
        # Perform translation
        try:
            translator = GoogleTranslator(source=source_code, target=target_code)
            translated = translator.translate(text)
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Translation failed: {str(e)}\n"
                f"Please check your language codes and try again.",
                ephemeral=True
            )
            return
        
        # Database operations (non-blocking - don't fail if these fail)
        try:
            await db.track_usage(user_id, text_chars=len(text))
        except Exception as e:
            logger.error(f"Failed to track usage: {e}")
        
        try:
            await db.save_translation(
                user_id=user_id,
                guild_id=interaction.guild_id,
                original_text=text,
                translated_text=translated,
                source_lang=source_code,
                target_lang=target_code,
                translation_type="text"
            )
        except Exception as e:
            logger.error(f"Failed to save translation: {e}")
        
        # Achievement tracking (non-blocking)
        try:
            achievement_db.track_translation(
                user_id,
                source_code,
                target_code,
                is_premium
            )
            
            new_achievements = achievement_db.check_achievements(user_id)
            if new_achievements:
                asyncio.create_task(
                    send_achievement_notification(client, user_id, new_achievements)
                )
        except Exception as e:
            logger.error(f"Failed to track achievements: {e}")
        
        # Calculate points awarded
        base_points = 1
        length_bonus = min(len(text) // 50, 5)  # 1 extra point per 50 chars, max 5
        premium_multiplier = 2 if is_premium else 1
        points_awarded = (base_points + length_bonus) * premium_multiplier
        
        # Award points (non-blocking)
        points_success = False
        try:
            safe_db_operation(reward_db.add_points, user_id, points_awarded, "Text translation")
            safe_db_operation(reward_db.increment_stat, user_id, 'text_translations')
            safe_db_operation(reward_db.increment_stat, user_id, 'total_translations')
            points_success = True
            logger.info(f"Successfully awarded {points_awarded} points to user {user_id}")
        except Exception as e:
            logger.error(f"Error awarding points to user {user_id}: {e}")
        
        # Get language display info
        source_name = languages.get(source_code, source_code)
        target_name = languages.get(target_code, target_code)
        source_flag = flag_mapping.get(source_code, '🌐')
        target_flag = flag_mapping.get(target_code, '🌐')
        
        # Create embed
        embed = discord.Embed(
            title="Text Translation",
            color=0x2ecc71 if is_premium else 0x3498db
        )
        
        # Add translation fields based on hidden status
        if user_id in hidden_sessions:
            # Only show translation in hidden mode
            embed.add_field(
                name=f"{target_flag} Translation ({target_name})",
                value=translated[:1024],  # Discord field limit
                inline=False
            )
        else:
            # Show both original and translation
            embed.add_field(
                name=f"{source_flag} Original ({source_name})",
                value=text[:1024],  # Discord field limit
                inline=False
            )
            
            embed.add_field(
                name=f"{target_flag} Translation ({target_name})",
                value=translated[:1024],  # Discord field limit
                inline=False
            )
        
        
        # Add points field if successfully awarded
        # Add points field with debugging
        # Add points field with debugging
        if points_success and points_awarded > 0:
            try:
                print(f"🔍 DEBUG: About to display points")
                print(f"🔍 points_awarded type: {type(points_awarded)}")
                print(f"🔍 points_awarded value: {points_awarded}")
                print(f"🔍 Current embed field count: {len(embed.fields)}")
        
        # Convert to safe string
                points_str = str(int(points_awarded))
                print(f"🔍 points_str: {points_str}")
        
        # Try to add field
                embed.add_field(
                    name="💎",
                    value=f"+{points_str}",
                    inline=True
                )
                print(f"✅ Successfully added points field")
        
            except Exception as e:
                print(f"❌ Points display error: {e}")
                print(f"❌ Error type: {type(e)}")
                # Don't let points display break the whole command
                pass


        
        # Add footer with context info
        if interaction.guild:
            if is_premium:
                embed.set_footer(text=f"Server: {interaction.guild.name} • Premium User")
            else:
                embed.set_footer(
                    text=f"Characters: {len(text)}/{text_limit} • Server: {interaction.guild.name} • /upgrade for unlimited"
                )
        else:
            if is_premium:
                embed.set_footer(text="User Mode: DM Translation • Premium User")
            else:
                embed.set_footer(
                    text=f"Characters: {len(text)}/{text_limit} • User Mode: DM Translation • /upgrade for unlimited"
                )
        
        # Send the response
        await interaction.response.send_message(embed=embed)
        
    except Exception as e:
        logger.error(f"Unexpected error in text_translate: {e}")
        
        # Send error response if we haven't responded yet
        if not interaction.response.is_done():
            await interaction.response.send_message(
                f"❌ An unexpected error occurred. Please try again.\n"
                f"If the problem persists, contact support.",
                ephemeral=True
            )
        else:
            # If we already responded, send a followup
            try:
                await interaction.followup.send(
                    f"❌ An error occurred during processing: {str(e)}",
                    ephemeral=True
                )
            except:
                pass  # Can't send followup either, just log

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
        
        # NEW: Get effective limits including rewards
        user_id = interaction.user.id
        limits = get_effective_limits(user_id, tier_handler, reward_db)

        # Get user's tier limits
        user_id = interaction.user.id
        
        # Check text length against limits (per translation)
        can_translate, limit_message = await tier_handler.check_usage_limits(user_id, text_chars=len(text))
        if not can_translate:
            await interaction.response.send_message(
                f"🔒 {limit_message}\n💡 Try shorter text or use /upgrade for unlimited translation!",
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
        
        # NEW: Award points for voice synthesis
        points_awarded = 3 if user_id in tier_handler.premium_users else 2
        reward_db.add_points(user_id, points_awarded, f"Voice synthesis: {source_code}→{target_code}")

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

        # NEW: Add points earned indicator
        embed.add_field(
            name="💎 Points Earned",
            value=f"+{points_awarded}",
            inline=True
        )
        
        # Add character count for free users
        user = await db.get_or_create_user(user_id)
        if not user['is_premium']:
            embed.set_footer(text=f"Characters used: {len(text)}/150 • Upgrade: /upgrade")
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
    await track_command_usage(interaction)
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
    limits = get_effective_limits(user_id, tier_handler, reward_db)
    
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
                    "Use `/upgrade` to upgrade now!"
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

                 # NEW: Award points for voice translation
                points_awarded = 5 if user_id in tier_handler.premium_users else 2
                reward_db.add_points(user_id, points_awarded, f"Voice translation: {self.source_language}→{self.target_language}")
                
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
            points_per_translation = 5 if user_id in tier_handler.premium_users else 2
            embed.add_field(
                name="💎 Rewards",
                value=f"+{points_per_translation} points per translation",
                inline=True
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
                    value="Get unlimited voice translation with `/upgrade`",
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
    await track_command_usage(interaction)
    
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
    
    # NEW: Check if user has access to Enhanced Voice V2
    user_id = interaction.user.id
    
    # Check enhanced voice access using the new shop system
    if not has_enhanced_voice_access(user_id, reward_db, tier_handler):
        user_data = reward_db.get_or_create_user(user_id, interaction.user.display_name)
        current_tier = await tier_handler.get_user_tier_async(user_id)
        
        # Create access denied embed with purchase options
        embed = discord.Embed(
            title="🚀 Enhanced Voice V2 - Beta Feature",
            description="This advanced voice translation feature is currently in beta testing!",
            color=0x9b59b6
        )
        
        embed.add_field(
            name="💎 Your Points",
            value=f"{user_data['points']:,}",
            inline=True
        )
        
        embed.add_field(
            name="🛍️ Beta Access Options",
            value=(
                "• **1-Day Access:** 50 points\n"
                "• **Beta Trial (48h):** 100 points\n"
                "• **7-Day Access:** 300 points"
            ),
            inline=True
        )
        
        embed.add_field(
            name="⭐ Permanent Access",
            value=(
                "**Premium ($3/month):** Unlimited Enhanced Voice V2\n"
                "**Pro ($5/month):** All features + priority support\n"
                "Use `/upgrade` to upgrade!"
            ),
            inline=True
        )
        
        embed.add_field(
            name="🧪 Enhanced Voice V2 Features",
            value=(
                "• **Bidirectional translation** between any 2 languages\n"
                "• **Smart language detection** with priority matching\n"
                "• **Multi-speaker support** for group conversations\n"
                "• **Improved audio processing** for better accuracy"
            ),
            inline=False
        )
        
        embed.add_field(
            name="🎯 How to Get Points",
            value=(
                "• `/daily` - 5-25 points daily (tier-based)\n"
                "• Use translator regularly (+1-5 per use)\n"
                "• Complete achievements (+10-100)\n"
                "• Leave feedback (+15-30)"
            ),
            inline=False
        )
        
        embed.add_field(
            name="📊 Current Status",
            value=f"**Tier:** {current_tier.title()}\n**Access:** Basic voice features only",
            inline=False
        )
        
        # Add purchase buttons
        view = discord.ui.View()
        
        # 1-Day Access Button
        if user_data['points'] >= 50:
            view.add_item(discord.ui.Button(
                label="Buy 1-Day Access (50 points)",
                style=discord.ButtonStyle.green,
                custom_id="buy_enhanced_voice_1day"
            ))
        else:
            view.add_item(discord.ui.Button(
                label="1-Day Access (50 points) - Need more points",
                style=discord.ButtonStyle.gray,
                disabled=True
            ))
        
        # Beta Trial Button
        if user_data['points'] >= 100:
            view.add_item(discord.ui.Button(
                label="Buy Beta Trial (100 points)",
                style=discord.ButtonStyle.blurple,
                custom_id="buy_enhanced_voice_trial"
            ))
        else:
            view.add_item(discord.ui.Button(
                label="Beta Trial (100 points) - Need more points",
                style=discord.ButtonStyle.gray,
                disabled=True
            ))
        
        # 7-Day Access Button
        if user_data['points'] >= 300:
            view.add_item(discord.ui.Button(
                label="Buy 7-Day Access (300 points)",
                style=discord.ButtonStyle.red,
                custom_id="buy_enhanced_voice_7day"
            ))
        else:
            view.add_item(discord.ui.Button(
                label="7-Day Access (300 points) - Need more points",
                style=discord.ButtonStyle.gray,
                disabled=True
            ))
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        return
    
    # Convert language inputs to codes - support both codes and names
    source_code = "auto" if language1.lower() == "auto" else get_language_code(language1)
    target_code = "auto" if language2.lower() == "auto" else get_language_code(language2)
    
    # Validate language codes (at least one must not be auto)
    if language1.lower() != "auto" and not source_code:
        await interaction.response.send_message(
            f"❌ Invalid language: '{language1}'\nUse /list to see available languages or use 'auto' for automatic detection.",
            ephemeral=True
        )
        return
        
    if language2.lower() != "auto" and not target_code:
        await interaction.response.send_message(
            f"❌ Invalid language: '{language2}'\nUse /list to see available languages or use 'auto' for automatic detection.",
            ephemeral=True
        )
        return
    
    # Don't allow both languages to be auto
    if source_code == "auto" and target_code == "auto":
        await interaction.response.send_message(
            "❌ At least one language must be specified (not 'auto'). Example: `/voicechat2 auto english`",
            ephemeral=True
        )
        return
    
    # Get user's tier limits
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
                
                # NEW: Award enhanced points for V2 usage
                points_awarded = 10 if user_id in tier_handler.premium_users else 5
                reward_db.add_points(user_id, points_awarded, f"Enhanced Voice V2: {detected_lang}→{target_lang}")
                
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
                embed.set_footer(text=f"Enhanced V2 | Language pair: {lang1_display} ↔ {lang2_display} | +{points_awarded} points")
                
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
            language1=source_code,
            language2=target_code,
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
            lang1_display = "Auto-detect" if source_code == "auto" else languages.get(source_code, source_code)
            lang2_display = "Auto-detect" if target_code == "auto" else languages.get(target_code, target_code)
            lang1_flag = '🔍' if source_code == "auto" else flag_mapping.get(source_code, '🌐')
            lang2_flag = '🔍' if target_code == "auto" else flag_mapping.get(target_code, '🌐')
            
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
            
            # Add enhanced rewards info
            points_per_translation = 10 if user_id in tier_handler.premium_users else 5
            embed.add_field(
                name="💎 Enhanced Rewards",
                value=f"+{points_per_translation} points per translation\n(2x regular voice chat)",
                inline=True
            )
            
            # Add examples based on the language pair
            if source_code != "auto" and target_code != "auto":
                embed.add_field(
                    name="📝 How it works",
                    value=(
                        f"• Speak in {lang1_display} → Translates to {lang2_display}\n"
                        f"• Speak in {lang2_display} → Translates to {lang1_display}\n"
                        f"• Other languages → Translates to {lang2_display} (default)"
                    ),
                    inline=False
                )
            elif source_code == "auto":
                embed.add_field(
                    name="📝 How it works",
                    value=f"• Speak in any language → Translates to {lang2_display}",
                    inline=False
                )
            else:  # target_code == "auto"
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
                'type': 'enhanced_v2',
                                'languages': [source_code, target_code]
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

# Add autocomplete to the command
voice_chat_translate_bidirectional_v2.autocomplete('language1')(source_language_autocomplete)
voice_chat_translate_bidirectional_v2.autocomplete('language2')(source_language_autocomplete)

# Add button interaction handler for Enhanced Voice V2 purchases
@client.event
async def on_interaction(interaction):
    if interaction.type == discord.InteractionType.component:
        custom_id = interaction.data.get('custom_id')
        user_id = interaction.user.id
        
        if custom_id in ['buy_enhanced_voice_1day', 'buy_enhanced_voice_trial', 'buy_enhanced_voice_7day']:
            user_data = reward_db.get_or_create_user(user_id, interaction.user.display_name)
            
            # Define purchase options
            purchase_options = {
                'buy_enhanced_voice_1day': {'cost': 50, 'duration': 1, 'name': '1-Day Access'},
                'buy_enhanced_voice_trial': {'cost': 100, 'duration': 2, 'name': 'Beta Trial (48h)'},
                'buy_enhanced_voice_7day': {'cost': 300, 'duration': 7, 'name': '7-Day Access'}
            }
            
            option = purchase_options[custom_id]
            
            # Check if user has enough points
            if user_data['points'] < option['cost']:
                await interaction.response.send_message(
                    f"❌ Insufficient points! You need {option['cost']} points but only have {user_data['points']}.",
                    ephemeral=True
                )
                return
            
            # Process the purchase
            try:
                # Deduct points
                reward_db.add_points(user_id, -option['cost'], f"Purchased Enhanced Voice V2: {option['name']}")
                
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
                    title="✅ Purchase Successful!",
                    description=f"You've successfully purchased **{option['name']}** for Enhanced Voice V2!",
                    color=0x2ecc71
                )
                
                embed.add_field(
                    name="💎 Points Spent",
                    value=f"{option['cost']} points",
                    inline=True
                )
                
                embed.add_field(
                    name="💰 Remaining Points",
                    value=f"{user_data['points'] - option['cost']} points",
                    inline=True
                )
                
                embed.add_field(
                    name="⏰ Access Expires",
                    value=f"{expiry_date.strftime('%Y-%m-%d %H:%M UTC')}",
                    inline=False
                )
                
                embed.add_field(
                    name="🚀 Ready to Use!",
                    value="You can now use `/voicechat2` for enhanced voice translation!",
                    inline=False
                )
                
                await interaction.response.send_message(embed=embed, ephemeral=True)
                
            except Exception as e:
                logger.error(f"Error processing Enhanced Voice V2 purchase: {e}")
                await interaction.response.send_message(
                    "❌ An error occurred while processing your purchase. Please try again.",
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
                f"🔒 {limit_message}\n💡 Try shorter text or use /upgrade for unlimited translation!",
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
            embed.set_footer(text=f"Characters: {len(text)}/150 • Server: {interaction.guild.name} • /upgrade for unlimited")
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
    await track_command_usage(interaction)  # NEW: Track usage for points
    
    user_id = interaction.user.id
    guild_id = interaction.guild_id
    
    # Track if we found and stopped any sessions
    stopped_any = False
    
    # NEW: End user session for point tracking
    if user_id in user_sessions:
        session_data = user_sessions[user_id]
        if session_data.get('active', False):
            # Calculate session duration
            session_duration = (datetime.now() - session_data['session_start']).total_seconds() / 3600  # hours
            
            # Award session completion bonus
            session_bonus = max(1, int(session_duration * 5))  # 5 points per hour
            if user_id in tier_handler.premium_users:
                session_bonus *= 2
            
            reward_db.add_points(user_id, session_bonus, f"Session completion bonus ({session_duration:.1f}h)")
            reward_db.update_usage_time(user_id, session_duration)
            
            user_sessions[user_id]['active'] = False
            stopped_any = True
    
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
        # NEW: Create enhanced stop message with session stats
        embed = discord.Embed(
            title="🛑 Translation Session Ended",
            description="All active translation sessions have been stopped.",
            color=0xe74c3c
        )
        
        # Add session stats if available
        if user_id in user_sessions and 'session_start' in user_sessions[user_id]:
            session_duration = (datetime.now() - user_sessions[user_id]['session_start']).total_seconds()
            commands_used = user_sessions[user_id].get('commands_used', 0)
            
            embed.add_field(
                name="📊 Session Stats",
                value=f"⏱️ Duration: {session_duration/60:.1f} minutes\n🔧 Commands used: {commands_used}",
                inline=True
            )
            
            if user_id in user_sessions and user_sessions[user_id].get('active', False):
                session_bonus = max(1, int((session_duration / 3600) * 5))
                if user_id in tier_handler.premium_users:
                    session_bonus *= 2
                
                embed.add_field(
                    name="💎 Session Bonus",
                    value=f"+{session_bonus} points",
                    inline=True
                )
        
        embed.add_field(
            name="💡 Tip",
            value="Use `/daily` to claim your daily points!",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        await interaction.response.send_message("No active translation session found!", ephemeral=True)


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
                            f"💡 Try shorter messages or use /upgrade for unlimited translation!"
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

                # NEW: Award points for auto-translation
                points_awarded = 3 if user_id in tier_handler.premium_users else 1
                reward_db.add_points(user_id, points_awarded, f"Auto-translation: {source_code}→{target_code}")
                
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

                # NEW: Add points earned indicator (smaller for auto-translation)
                embed.add_field(
                    name="💎",
                    value=f"+{points_awarded}",
                    inline=True
                )

                # Add character count for free users
                user = await db.get_or_create_user(user_id)
                if not user['is_premium']:
                    embed.set_footer(text=f"Characters: {len(message.content)}/150 • Auto-translate • /upgrade for unlimited")
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
                f"🔒 {limit_message}\n💡 Try shorter text or use /upgrade for unlimited translation!",
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
                sender_embed.set_footer(text=f"Characters used: {len(text)}/150 • /upgrade for unlimited")
            
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
    await track_command_usage(interaction)
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
                f"🔒 {limit_message}\n💡 Try a shorter message or use /upgrade for unlimited translation!",
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
        
        # NEW: Award points for message reading
        points_awarded = 2 if user_id in tier_handler.premium_users else 1
        reward_db.add_points(user_id, points_awarded, f"Message read: {source_lang}→{target_code}")
        
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
        # NEW: Add points earned indicator
        embed.add_field(
            name="💎 Points Earned",
            value=f"+{points_awarded}",
            inline=True
        )
        
        
        # Add character count for free users
        user = await db.get_or_create_user(user_id)
        if not user['is_premium']:
            footer_text = f"Characters: {len(message_to_translate.content)}/150 • From: {message_to_translate.author.display_name} • /upgrade for unlimited"
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
    await track_command_usage(interaction)
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
        # NEW: Get effective limits including rewards
        user_id = interaction.user.id
        limits = get_effective_limits(user_id, tier_handler, reward_db)

        # Get user's tier limits and check usage
        user_id = interaction.user.id
        can_translate, limit_message = await tier_handler.check_usage_limits(user_id, text_chars=len(message.content))
        if not can_translate:
            await interaction.response.send_message(
                f"🔒 {limit_message}\n💡 Try a shorter message or use /upgrade for unlimited translation!",
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
                
                # NEW: Award points for context menu translation
                points_awarded = 2 if self.user_id in tier_handler.premium_users else 1
                reward_db.add_points(self.user_id, points_awarded, f"Context menu translation: {source_lang}→{target_code}")
                
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

                # NEW: Add points earned indicator
                embed.add_field(
                    name="💎 Points Earned",
                    value=f"+{points_awarded}",
                    inline=True
                )
                
                # Add character count for free users
                user = await db.get_or_create_user(modal_interaction.user.id)
                if not user['is_premium']:
                    footer_text = f"Characters: {len(self.message_to_translate.content)}/150 • From: {self.message_to_translate.author.display_name} • /upgrade for unlimited"
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
@tree.command(name="achievements", description="View your achievements, badges, and progress")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def achievements(interaction: discord.Interaction):
    await track_command_usage(interaction)
    
    try:
        user_id = interaction.user.id
        username = interaction.user.display_name
        
        # Get user data from both systems
        user_data = reward_db.get_or_create_user(user_id, username)
        stats = achievement_db.get_user_stats(user_id) if 'achievement_db' in globals() else user_data
        achievements = reward_db.get_user_achievements(user_id)
        badges = reward_db.get_user_badges(user_id, achievements, user_data['points'])
        
        # Get user rank
        rank_info = get_rank_from_points(user_data['points'])
        
        # Create main embed
        embed = discord.Embed(
            title=f"🏆 {username}'s Achievements & Badges",
            color=rank_info.get('color', 0xf1c40f)
        )
        
        # Add rank and points section
        embed.add_field(
            name="📊 Rank & Points",
            value=f"{rank_info.get('name', 'Unranked')}\n**{user_data['points']:,}** total points",
            inline=True
        )
        
        # Add achievement count
        total_achievements = len(ALL_ACHIEVEMENTS) if 'ALL_ACHIEVEMENTS' in globals() else 12
        embed.add_field(
            name="🎯 Achievements",
            value=f"**{len(achievements)}** / **{total_achievements}** unlocked",
            inline=True
        )
        
        # Add stats summary
        embed.add_field(
            name="📈 Statistics",
            value=(
                f"**{user_data.get('total_translations', 0)}** translations\n"
                f"**{user_data.get('total_sessions', 0)}** sessions\n"
                f"**{len(user_data.get('languages_used', []))}** languages used"
            ),
            inline=True
        )
        
        # Show unlocked badges
        if badges:
            badge_text = ""
            for badge in badges[:5]:  # Show first 5 badges
                badge_text += f"{badge['emoji']} **{badge['title']}**"
                if badge['type'] == 'rank':
                    badge_text += " (Rank Badge)\n"
                else:
                    badge_text += " (Achievement Badge)\n"
            
            embed.add_field(
                name="🎖️ Unlocked Badges",
                value=badge_text,
                inline=False
            )
        
        # Show recent achievements
        if achievements:
            recent_achievements = achievements[-3:]  # Last 3 achievements
            achievement_text = ""
            
            for ach in recent_achievements:
                # Get achievement data
                ach_data = ALL_ACHIEVEMENTS.get(ach, {}) if 'ALL_ACHIEVEMENTS' in globals() else {}
                rarity_info = RARITY_INFO.get(ach_data.get('rarity', 'common'), {}) if 'RARITY_INFO' in globals() else {}
                
                achievement_text += f"{rarity_info.get('emoji', '⭐')} **{ach_data.get('name', ach)}**\n"
            
            embed.add_field(
                name="🎉 Recent Achievements",
                value=achievement_text,
                inline=False
            )
        
        # Show progress towards next achievements
        locked_achievements = []
        all_achievements = {
            'first_translation': {'name': '🌟 First Steps', 'desc': 'Complete your first translation', 'requirement': 1, 'stat': 'translations'},
            'translation_10': {'name': '📈 Getting Started', 'desc': 'Complete 10 translations', 'requirement': 10, 'stat': 'translations'},
            'translation_50': {'name': '🎯 Dedicated', 'desc': 'Complete 50 translations', 'requirement': 50, 'stat': 'translations'},
            'translation_100': {'name': '👑 Master', 'desc': 'Complete 100 translations', 'requirement': 100, 'stat': 'translations'},
            'translation_500': {'name': '🏆 Legend', 'desc': 'Complete 500 translations', 'requirement': 500, 'stat': 'translations'},
            'languages_5': {'name': '🌍 Explorer', 'desc': 'Use 5 different languages', 'requirement': 5, 'stat': 'languages'},
            'languages_15': {'name': '🌎 Polyglot', 'desc': 'Use 15 different languages', 'requirement': 15, 'stat': 'languages'},
            'languages_30': {'name': '🌏 Linguist', 'desc': 'Use 30 different languages', 'requirement': 30, 'stat': 'languages'},
            'first_voice': {'name': '🎤 Voice User', 'desc': 'Use voice translation', 'requirement': 1, 'stat': 'voice'},
            'voice_25': {'name': '📻 Voice Veteran', 'desc': 'Use voice translation 25 times', 'requirement': 25, 'stat': 'voice'},
            'premium_supporter': {'name': '⭐ Supporter', 'desc': 'Purchase premium', 'requirement': 'premium', 'stat': 'premium'},
            'early_adopter': {'name': '🚀 Pioneer', 'desc': 'Early bot user', 'requirement': 'early', 'stat': 'early'}
        }
        
        # Find next achievable achievements
        for ach_id, ach_data in all_achievements.items():
            if ach_id not in achievements:
                current_progress = 0
                requirement = ach_data['requirement']
                
                if ach_data['stat'] == 'translations':
                    current_progress = user_data.get('total_translations', 0)
                elif ach_data['stat'] == 'languages':
                    current_progress = len(user_data.get('languages_used', []))
                elif ach_data['stat'] == 'voice':
                    current_progress = user_data.get('total_sessions', 0)
                elif ach_data['stat'] == 'premium':
                    if user_id in tier_handler.premium_users:
                        continue  # Should be unlocked
                    else:
                        locked_achievements.append(f"🔒 {ach_data['name']} - {ach_data['desc']}")
                        continue
                elif ach_data['stat'] == 'early':
                    locked_achievements.append(f"🔒 {ach_data['name']} - {ach_data['desc']}")
                    continue
                
                if isinstance(requirement, int) and current_progress < requirement:
                    progress_bar = "█" * min(5, int((current_progress / requirement) * 5))
                    progress_bar += "░" * (5 - len(progress_bar))
                    locked_achievements.append(f"🔓 {ach_data['name']} - {progress_bar} {current_progress}/{requirement}")
        
        if locked_achievements:
            embed.add_field(
                name="🎯 Next Achievements",
                value="\n".join(locked_achievements[:4]),  # Show first 4
                inline=False
            )
        
        # Show rank progression
        current_rank = None
        next_rank = None
        
        if 'RANK_BADGES' in globals():
            for min_points in sorted(RANK_BADGES.keys(), reverse=True):
                if user_data['points'] >= min_points:
                    current_rank = RANK_BADGES[min_points]
                    break
            
            for min_points in sorted(RANK_BADGES.keys()):
                if user_data['points'] < min_points:
                    next_rank = RANK_BADGES[min_points]
                    points_needed = min_points - user_data['points']
                    break
            
            if next_rank:
                embed.add_field(
                    name="📈 Next Rank",
                    value=f"{next_rank['emoji']} {next_rank['title']}\nNeed {points_needed:,} more points",
                    inline=True
                )
        
        # Add context info
        if interaction.guild:
            embed.set_footer(text=f"Server: {interaction.guild.name} • Use buttons below for more details")
        else:
            embed.set_footer(text="🏆 Achievement System • Use buttons below for more details")
        
        # Create view with buttons
        view = IntegratedAchievementView(user_id)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Achievements command error: {e}")
        await interaction.response.send_message(
            "❌ An error occurred while fetching your achievements. Please try again later.",
            ephemeral=True
        )

class IntegratedAchievementView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=300)
        self.user_id = user_id

    @discord.ui.button(label="📋 All Achievements", style=discord.ButtonStyle.primary)
    async def all_achievements(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            user_data = reward_db.get_or_create_user(self.user_id, interaction.user.display_name)
            achievements = reward_db.get_user_achievements(self.user_id)
            
            embed = discord.Embed(
                title="📋 All Achievements",
                description="Your complete achievement collection:",
                color=0x3498db
            )
            
            # Define all achievements with categories
            achievement_categories = {
                "🌟 Translation Milestones": {
                    'first_translation': {'name': '🌟 First Steps', 'desc': 'Complete your first translation', 'points': 25},
                    'translation_10': {'name': '📈 Getting Started', 'desc': 'Complete 10 translations', 'points': 50},
                    'translation_50': {'name': '🎯 Dedicated', 'desc': 'Complete 50 translations', 'points': 100},
                    'translation_100': {'name': '👑 Master', 'desc': 'Complete 100 translations', 'points': 200},
                    'translation_500': {'name': '🏆 Legend', 'desc': 'Complete 500 translations', 'points': 500}
                },
                "🌍 Language Explorer": {
                    'languages_5': {'name': '🌍 Explorer', 'desc': 'Use 5 different languages', 'points': 75},
                    'languages_15': {'name': '🌎 Polyglot', 'desc': 'Use 15 different languages', 'points': 150},
                    'languages_30': {'name': '🌏 Linguist', 'desc': 'Use 30 different languages', 'points': 300}
                },
                "🎤 Voice Features": {
                    'first_voice': {'name': '🎤 Voice User', 'desc': 'Use voice translation', 'points': 50},
                    'voice_25': {'name': '📻 Voice Veteran', 'desc': 'Use voice translation 25 times', 'points': 200}
                },
                "⭐ Special": {
                    'premium_supporter': {'name': '⭐ Supporter', 'desc': 'Purchase premium', 'points': 500},
                    'early_adopter': {'name': '🚀 Pioneer', 'desc': 'Early bot user', 'points': 100}
                }
            }
            
            # Add fields for each category
            for category, ach_list in achievement_categories.items():
                category_text = ""
                for ach_id, ach_data in ach_list.items():
                    status = "✅" if ach_id in achievements else "❌"
                    category_text += f"{status} **{ach_data['name']}** ({ach_data['points']} pts)\n    {ach_data['desc']}\n\n"
                
                embed.add_field(
                    name=category,
                    value=category_text,
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"All achievements error: {e}")
            await interaction.response.send_message("❌ Error loading achievements.", ephemeral=True)

    @discord.ui.button(label="🎯 Progress", style=discord.ButtonStyle.secondary)
    async def progress(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            user_data = reward_db.get_or_create_user(self.user_id, interaction.user.display_name)
            achievements = reward_db.get_user_achievements(self.user_id)
            
            embed = discord.Embed(
                title="🎯 Achievement Progress",
                description="Your progress towards unearned achievements:",
                color=0x2ecc71
            )
            
            # Progress tracking
            progress_data = [
                ('first_translation', 'First Steps', user_data.get('total_translations', 0), 1),
                ('translation_10', 'Getting Started', user_data.get('total_translations', 0), 10),
                ('translation_50', 'Dedicated', user_data.get('total_translations', 0), 50),
                ('translation_100', 'Master', user_data.get('total_translations', 0), 100),
                ('translation_500', 'Legend', user_data.get('total_translations', 0), 500),
                ('languages_5', 'Explorer', len(user_data.get('languages_used', [])), 5),
                ('languages_15', 'Polyglot', len(user_data.get('languages_used', [])), 15),
                ('languages_30', 'Linguist', len(user_data.get('languages_used', [])), 30),
                ('first_voice', 'Voice User', user_data.get('total_sessions', 0), 1),
                ('voice_25', 'Voice Veteran', user_data.get('total_sessions', 0), 25)
            ]
            
            progress_text = ""
            shown_count = 0
            
            for ach_id, name, current, requirement in progress_data:
                if ach_id in achievements or shown_count >= 8:
                    continue
                
                progress_percentage = min(100, int((current / requirement) * 100))
                progress_bar = "█" * min(10, int((current / requirement) * 10))
                progress_bar += "░" * (10 - len(progress_bar))
                
                progress_text += f"**{name}**\n{progress_bar} {current}/{requirement} ({progress_percentage}%)\n\n"
                shown_count += 1
            
            # Add special achievements
            if 'premium_supporter' not in achievements:
                premium_status = "✅ Ready to unlock!" if self.user_id in tier_handler.premium_users else "❌ Premium required"
                progress_text += f"**⭐ Premium Supporter**\n{premium_status}\n\n"
            
            if progress_text:
                embed.description = progress_text
            else:
                embed.description = "🎉 All trackable achievements unlocked! Amazing work!"
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Progress error: {e}")
            await interaction.response.send_message("❌ Error loading progress.", ephemeral=True)

    @discord.ui.button(label="📊 Leaderboard", style=discord.ButtonStyle.success)
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
                translations = user_data.get('total_translations', 0)
                
                try:
                    user = await client.fetch_user(user_id)
                    username = user.display_name if user else f"User {user_id}"
                except:
                    username = f"User {user_id}"
                
                # Get rank info
                rank_info = get_rank_from_points(points)
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                
                leaderboard_text += f"{medal} **{username}** - {points:,} pts\n"
                leaderboard_text += f"    {rank_info.get('name', 'Unranked')} • {translations} translations\n\n"
            
            embed.description = leaderboard_text
            
            # Add user's position if not in top 10
            user_position = reward_db.get_user_rank(self.user_id)
            if user_position and user_position > 10:
                user_data = reward_db.get_or_create_user(self.user_id, interaction.user.display_name)
                embed.add_field(
                    name="📍 Your Position",
                    value=f"#{user_position} - {user_data['points']:,} points",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Leaderboard error: {e}")
            await interaction.response.send_message("❌ Error loading leaderboard.", ephemeral=True)

    @discord.ui.button(label="🎖️ Badges", style=discord.ButtonStyle.secondary)
    async def badges(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            user_data = reward_db.get_or_create_user(self.user_id, interaction.user.display_name)
            achievements = reward_db.get_user_achievements(self.user_id)
            badges = reward_db.get_user_badges(self.user_id, achievements, user_data['points'])
            
            embed = discord.Embed(
                title="🎖️ Your Badge Collection",
                description="All your earned badges and ranks:",
                color=0x9b59b6
            )
            
            if not badges:
                embed.description = "No badges earned yet. Complete achievements and gain points to unlock badges!"
                embed.add_field(
                    name="💡 How to Earn Badges",
                    value=(
                        "🏅 **Rank Badges** - Earned by accumulating points\n"
                        "🎯 **Achievement Badges** - Earned by completing specific achievements\n"
                        "⭐ **Special Badges** - Earned through premium or special events"
                    ),
                    inline=False
                )
            else:
                # Separate badges by type
                rank_badges = [b for b in badges if b['type'] == 'rank']
                achievement_badges = [b for b in badges if b['type'] == 'achievement']
                special_badges = [b for b in badges if b['type'] == 'special']
                
                if rank_badges:
                    rank_text = ""
                    for badge in rank_badges:
                        rank_text += f"{badge['emoji']} **{badge['title']}**\n    {badge.get('description', 'Rank badge')}\n\n"
                    embed.add_field(name="🏅 Rank Badges", value=rank_text, inline=False)
                
                if achievement_badges:
                    ach_text = ""
                    for badge in achievement_badges[:5]:  # Limit to 5 to avoid embed limits
                        ach_text += f"{badge['emoji']} **{badge['title']}**\n    {badge.get('description', 'Achievement badge')}\n\n"
                    if len(achievement_badges) > 5:
                        ach_text += f"... and {len(achievement_badges) - 5} more!"
                    embed.add_field(name="🎯 Achievement Badges", value=ach_text, inline=False)
                
                if special_badges:
                    special_text = ""
                    for badge in special_badges:
                        special_text += f"{badge['emoji']} **{badge['title']}**\n    {badge.get('description', 'Special badge')}\n\n"
                    embed.add_field(name="⭐ Special Badges", value=special_text, inline=False)
            
            # Add badge count
            embed.add_field(
                name="📊 Badge Stats",
                value=f"**{len(badges)}** total badges earned\n**{user_data['points']:,}** achievement points",
                inline=True
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Badges error: {e}")
            await interaction.response.send_message("❌ Error loading badges.", ephemeral=True)

    async def on_timeout(self):
        # Disable all buttons when the view times out
        for item in self.children:
            item.disabled = True


def get_rank_from_points(points):
    """Get rank information based on points with safe fallback"""
    try:
        # Define basic ranks if not already defined
        global RANK_BADGES
        if 'RANK_BADGES' not in globals():
            RANK_BADGES = {
                0: {'name': '🆕 Newcomer', 'emoji': '🆕', 'color': 0x95a5a6},
                50: {'name': '🌱 Beginner', 'emoji': '🌱', 'color': 0x2ecc71},
                150: {'name': '📈 Learner', 'emoji': '📈', 'color': 0x3498db},
                300: {'name': '🎯 Dedicated', 'emoji': '🎯', 'color': 0x9b59b6},
                500: {'name': '⭐ Expert', 'emoji': '⭐', 'color': 0xf1c40f},
                1000: {'name': '👑 Master', 'emoji': '👑', 'color': 0xe67e22},
                2000: {'name': '🏆 Legend', 'emoji': '🏆', 'color': 0xe74c3c},
                5000: {'name': '💎 Grandmaster', 'emoji': '💎', 'color': 0x1abc9c}
            }
        
        current_rank = RANK_BADGES[0]  # Default to lowest rank
        
        for min_points in sorted(RANK_BADGES.keys(), reverse=True):
            if points >= min_points:
                current_rank = RANK_BADGES[min_points]
                break
        
        return current_rank
        
    except Exception as e:
        logger.error(f"Error getting rank from points: {e}")
        # Return safe fallback
        return {
            'name': '🆕 Newcomer',
            'emoji': '🆕',
            'color': 0x95a5a6
        }


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
        
        # 🌟 PREMIUM ACCESS: Only Ko-fi Subscriptions of $1+
        if donation_type == 'Subscription' and amount >= 1.00:
            # Calculate premium days based on amount
            if amount >= 12.00:  # Annual subscription
                premium_days = 365
            elif amount >= 6.00:  # 6-month subscription  
                premium_days = 180
            elif amount >= 3.00:  # 3-month subscription
                premium_days = 90
            else:  # Monthly subscription ($1+)
                premium_days = 30
            
            # Process premium in background
            asyncio.run_coroutine_threadsafe(
                process_kofi_premium(user_id, premium_days, data),
                client.loop
            )
            
            logger.info(f"Premium subscription processed for user {user_id}: {premium_days} days")
            return jsonify({'status': 'success', 'message': f'Premium subscription activated for {premium_days} days'})
        
        # 💎 POINTS ONLY: One-time donations (no premium access)
        elif donation_type == 'Donation' and amount >= 1.00:
            # Point conversion rates for one-time purchases
            point_packages = {
                1.00: 50,    # $1 = 50 points
                2.00: 110,   # $2 = 110 points (10% bonus)
                5.00: 300,   # $5 = 300 points (20% bonus)
                10.00: 650,  # $10 = 650 points (30% bonus)
            }
            
            # Calculate points
            if amount in point_packages:
                points_to_award = point_packages[amount]
            else:
                # Custom amount calculation
                points_to_award = int(amount * 50)  # Base: $1 = 50 points
                
                # Bonus for larger amounts
                if amount >= 10:
                    points_to_award = int(points_to_award * 1.3)  # 30% bonus
                elif amount >= 5:
                    points_to_award = int(points_to_award * 1.2)  # 20% bonus
                elif amount >= 2:
                    points_to_award = int(points_to_award * 1.1)  # 10% bonus
            
            # Award points only (no premium)
            safe_db_operation(reward_db.add_points, user_id, points_to_award, f"Ko-fi donation (${amount})")
            
            # Send points notification
            asyncio.run_coroutine_threadsafe(
                send_points_only_notification(user_id, points_to_award, amount),
                client.loop
            )
            
            logger.info(f"Awarded {points_to_award} points to user {user_id} for ${amount} donation (no premium)")
            return jsonify({'status': 'success', 'message': f'{points_to_award} points awarded'})
        
        else:
            return jsonify({'status': 'ignored', 'message': 'Amount too low or invalid type'})
            
    except Exception as e:
        logger.error(f"Ko-fi webhook error: {e}")
        return jsonify({'status': 'error', 'message': str(e)})

# Keep your existing process_kofi_premium function as-is
async def process_kofi_premium(user_id: int, days: int, kofi_data):
    """Process Ko-fi premium in background"""
    try:
        from datetime import datetime, timedelta
        expires_at = datetime.now() + timedelta(days=days)
        
        # Create user if doesn't exist
        await db.get_or_create_user(user_id, f"Ko-fi User {user_id}")
        
        # Add premium to database
        await db.update_user_premium(user_id, True, expires_at)
        
        # Add to memory for immediate effect
        tier_handler.premium_users.add(user_id)
        
        # Try to notify the user
        try:
            user = await client.fetch_user(user_id)
            embed = discord.Embed(
                title="🌟 Premium Subscription Activated!",
                description=(
                    f"Thank you for your ${kofi_data['amount']} subscription!\n\n"
                    f"**Premium Duration:** {days} days\n"
                    f"**Expires:** {expires_at.strftime('%B %d, %Y')}\n\n"
                    f"✨ All premium features are now active!"
                ),
                color=0x29abe0
            )
            embed.add_field(
                name="⭐ Premium Features",
                value="• Unlimited character translation\n• Extended voice translation\n• Priority support",
                inline=False
            )
            await user.send(embed=embed)
            print(f"✅ Notified user {user_id} about premium subscription")
        except Exception as notify_error:
            print(f"⚠️ Couldn't notify user {user_id}: {notify_error}")
        
        print(f"✅ Successfully granted {days} days premium to user {user_id}")
        
    except Exception as e:
        print(f"❌ Error processing Ko-fi premium for user {user_id}: {e}")

# Add this new notification function for points-only purchases
async def send_points_only_notification(user_id: int, points: int, amount: float):
    try:
        user = await client.fetch_user(user_id)
        if user:
            embed = discord.Embed(
                title="💎 Points Purchased!",
                description=f"Thank you for your ${amount:.2f} donation!",
                color=0x3498db
            )
            embed.add_field(
                name="💰 Points Awarded",
                value=f"**{points:,} points** added to your account!",
                inline=False
            )
            embed.add_field(
                name="⭐ Want Premium Access?",
                value="Set up a **$1/month subscription** on Ko-fi for unlimited features!",
                inline=False
            )
            embed.add_field(
                name="🎯 Use Your Points",
                value="Use `/shop` to see what you can buy with points!",
                inline=False
            )
            await user.send(embed=embed)
    except Exception as e:
        logger.error(f"Failed to send points notification: {e}")

@tree.command(name="upgrade", description="Get premium access through Ko-fi")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def premium(interaction: discord.Interaction):
    embed = discord.Embed(
        title="💎 Upgrade Your Translation Experience",
        description="Choose the perfect plan for your needs:",
        color=0x29abe0
    )
    
    # Free Tier (current)
    embed.add_field(
        name="🆓 Free Tier",
        value=(
            "• 50 character limit per translation\n"
            "• 30 minutes total voice time\n"
            "• Basic features only\n"
        ),
        inline=True
    )
    
    # Basic Tier - $1/month
    embed.add_field(
        name="🥉 Basic - $1/month",
        value=(
            "• 500 character limit per translation\n"
            "• 1 hour total voice time\n"
            "• Translation history\n"
            "• Auto-translate feature\n"
        ),
        inline=True
    )
    
    # Premium Tier - $3/month
    embed.add_field(
        name="🥈 Premium - $3/month",
        value=(
            "• 2000 character limit per translation\n"
            "• 2 hours total voice time\n"
            "• Priority processing\n"
            "• Enhanced voice features\n"
            "• All Basic features\n"
        ),
        inline=True
    )
    
    # Pro Tier - $5/month
    embed.add_field(
        name="🥇 Pro - $5/month",
        value=(
            "• ♾️ Unlimited character limit\n"
            "• ♾️ Unlimited voice time\n"
            "• Priority support\n"
            "• Beta feature access\n"
            "• Custom integrations\n"
        ),
        inline=True
    )
    
    embed.add_field(
        name="📝 How to Subscribe",
        value=(
            f"1. Click the Ko-fi link below\n"
            f"2. Include your Discord ID: `{interaction.user.id}`\n"
            f"3. Choose your monthly tier\n"
            f"4. Get instant access!"
        ),
        inline=False
    )
    
    embed.add_field(
        name="🎁 Try Before You Buy",
        value=(
            "Use `/shop` to try premium features with points!\n"
            "• Basic (1 day): 75 points\n"
            "• Premium (1 day): 150 points\n"
            "• Pro (1 day): 250 points"
        ),
        inline=False
    )
    
    view = discord.ui.View()
    view.add_item(discord.ui.Button(
        label="Subscribe on Ko-fi",
        url="https://ko-fi.com/muse/tiers",
        style=discord.ButtonStyle.link,
        emoji="☕"
    ))
    
    await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


@tree.command(name="buypoints", description="Purchase points with one-time Ko-fi donation")
async def buy_points(interaction: discord.Interaction):
    user_id = interaction.user.id
    
    embed = discord.Embed(
        title="💎 Buy Points (One-Time Purchase)",
        description="Purchase points for special features and rewards!",
        color=0x3498db
    )
    
    embed.add_field(
        name="💰 Point Packages",
        value=(
            "💵 **$1** = 50 points\n"
            "💵 **$2** = 110 points *(10% bonus)*\n"
            "💵 **$5** = 300 points *(20% bonus)*\n"
            "💵 **$10** = 650 points *(30% bonus)*"
        ),
        inline=False
    )
    
    embed.add_field(
        name="⚠️ Points vs Premium",
        value=(
            "**Points:** One-time purchases, buy specific features\n"
            "**Premium:** $1/month subscription, unlimited everything"
        ),
        inline=False
    )
    
    embed.add_field(
        name="📝 How to Purchase Points",
        value=(
            f"1. Click the Ko-fi button below\n"
            f"2. Make a **one-time donation** (not subscription)\n"
            f"3. Include your Discord ID: `{user_id}`\n"
            f"4. Points added instantly!"
        ),
        inline=False
    )
    
    view = discord.ui.View()
    view.add_item(discord.ui.Button(
        label="💎 Buy Points on Ko-fi",
        url="https://ko-fi.com/yourusername",
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

@tree.command(name="status", description="Check your subscription status and account info")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def check_status(interaction: discord.Interaction):
    await track_command_usage(interaction)
    
    user_id = interaction.user.id
    
    # Get current tier (async for database accuracy)
    current_tier = await tier_handler.get_user_tier_async(user_id)
    limits = await tier_handler.get_limits_async(user_id)
    user_data = reward_db.get_or_create_user(user_id, interaction.user.display_name)
    active_rewards = reward_db.get_active_rewards(user_id)
    
    # Get tier display info
    tier_info = tier_handler.get_tier_info(current_tier)
    
    embed = discord.Embed(
        title=f"{tier_info['emoji']} Account Status",
        color=tier_info['color']
    )
    
    # Tier info with price
    tier_display = f"{tier_info['name']}"
    if current_tier != 'free':
        tier_display += f" ({tier_info['price']})"
    
    embed.add_field(
        name="⭐ Subscription Tier",
        value=tier_display,
        inline=True
    )
    
    # Points and rank
    rank = reward_db.get_user_rank(user_id)
    embed.add_field(
        name="💎 Points",
        value=f"{user_data['points']:,}",
        inline=True
    )
    
    embed.add_field(
        name="🏆 Rank",
        value=f"#{rank}" if rank else "Unranked",
        inline=True
    )
    
    # Current limits (enhanced by active rewards)
    text_limit = "Unlimited" if limits['text_limit'] == float('inf') else f"{limits['text_limit']} chars"
    voice_limit_display = "Unlimited" if limits['voice_limit'] == float('inf') else f"{limits['voice_limit']//60} min total"
    
    embed.add_field(
        name="📝 Text Limit",
        value=text_limit,
        inline=True
    )
    
    embed.add_field(
        name="🎤 Voice Limit",
        value=voice_limit_display,
        inline=True
    )
    
    embed.add_field(
        name="📊 Usage Stats",
        value=f"{user_data['total_usage_hours']:.1f}h • {user_data['total_sessions']} sessions",
        inline=True
    )
    
    # Active rewards
    if active_rewards:
        from datetime import datetime
        reward_text = "\n".join([
            f"• {reward['name']} (expires <t:{int(datetime.fromisoformat(reward['expires_at']).timestamp())}:R>)"
            for reward in active_rewards[:3]
        ])
        if len(active_rewards) > 3:
            reward_text += f"\n• +{len(active_rewards) - 3} more..."
            
        embed.add_field(
            name="🎁 Active Rewards",
            value=reward_text,
            inline=False
        )
    
    # Daily reward status
    from datetime import datetime
    today = datetime.now().date().isoformat()
    if user_data['last_daily_claim'] == today:
        daily_status = "✅ Claimed today"
    else:
        daily_status = "🎁 Available - use `/daily`"
    
    embed.add_field(
        name="🎁 Daily Reward",
        value=daily_status,
        inline=True
    )
    
    # Enhanced voice access (check for premium+ tiers or temp rewards)
    has_enhanced_voice = (current_tier in ['premium', 'pro'] or 
                         has_enhanced_voice_access(user_id, reward_db, tier_handler))
    embed.add_field(
        name="🚀 Enhanced Voice V2",
        value="✅ Available" if has_enhanced_voice else "❌ Not available",
        inline=True
    )
    
    # Show available features based on tier
    features = limits.get('features', [])
    feature_icons = {
        'basic_translation': '📝 Basic Translation',
        'history': '📚 Translation History', 
        'auto_translate': '🔄 Auto-translate',
        'priority_processing': '⚡ Priority Processing',
        'enhanced_voice': '🚀 Enhanced Voice',
        'all_features': '✨ All Features',
        'beta_access': '🧪 Beta Access',
        'priority_support': '🎯 Priority Support',
        'custom_integrations': '🔧 Custom Integrations'
    }
    
    feature_list = []
    for feature in features:
        if feature in feature_icons:
            feature_list.append(feature_icons[feature])
    
    if feature_list:
        embed.add_field(
            name="🎯 Your Features",
            value="\n".join(feature_list[:6]),  # Limit to 6 features to avoid embed limits
            inline=True
        )
    
    # Upgrade suggestions based on current tier
    if current_tier == 'free':
        embed.add_field(
            name="🚀 Upgrade to Basic ($1/month)",
            value="• 10x character limit (500 chars)\n• 2x voice time (60 min)\n• Translation history\n• Auto-translate feature",
            inline=False
        )
    elif current_tier == 'basic':
        embed.add_field(
            name="🚀 Upgrade to Premium ($3/month)", 
            value="• 4x character limit (2000 chars)\n• 2x voice time (2 hours)\n• Priority processing\n• Enhanced voice features",
            inline=False
        )
    elif current_tier == 'premium':
        embed.add_field(
            name="🚀 Upgrade to Pro ($5/month)",
            value="• ♾️ Unlimited everything\n• 🧪 Beta feature access\n• 🎯 Priority support\n• 🔧 Custom integrations",
            inline=False
        )
    else:  # Pro tier
        embed.add_field(
            name="🥇 Pro Member Benefits",
            value="• ♾️ Unlimited translations\n• 🧪 Early access to new features\n• 🎯 Priority support\n• 🔧 Custom integrations",
            inline=False
        )
    
    # Add usage efficiency tip
    if current_tier == 'free' and user_data['total_sessions'] > 5:
        embed.add_field(
            name="💡 Pro Tip",
            value="You're an active user! Consider upgrading for unlimited translations and premium features.",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)
@tree.command(name="history", description="View your recent translation history")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
@app_commands.describe(limit="Number of translations to show (max varies by tier)")
async def translation_history(interaction: discord.Interaction, limit: int = 10):
    await track_command_usage(interaction)
    
    user_id = interaction.user.id
    
    # Get current tier and check if history feature is available
    current_tier = await tier_handler.get_user_tier_async(user_id)
    limits = await tier_handler.get_limits_async(user_id)
    features = limits.get('features', [])
    
    # Check if user has access to history feature
    if 'history' not in features and current_tier == 'free':
        # Check for temporary history access from rewards
        has_temp_history = reward_db.has_active_reward(user_id, 'translation_history')
        
        if not has_temp_history:
            embed = discord.Embed(
                title="🔒 Feature Locked",
                description="Translation history is available for Basic tier and above!",
                color=0xe74c3c
            )
            
            embed.add_field(
                name="🥉 Basic Tier ($1/month)",
                value="• Translation history access\n• 500 character limit\n• 30 minutes voice time\n• Auto-translate feature",
                inline=False
            )
            
            embed.add_field(
                name="🎁 Try It Now",
                value="Use `/shop` to get temporary history access with points!\nOr upgrade to Basic for permanent access.",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
    
    # Set limits based on tier
    tier_limits = {
        'free': 5,      # Free users with temp access get 5
        'basic': 15,    # Basic users get 15
        'premium': 30,  # Premium users get 30
        'pro': 50       # Pro users get 50
    }
    
    max_limit = tier_limits.get(current_tier, 5)
    limit = min(limit, max_limit)
    
    # Get user data for display
    user_data = reward_db.get_or_create_user(user_id, interaction.user.display_name)
    
    # Get translation history using your database method
    try:
        history = await db.get_translation_history(user_id, limit)
    except Exception as e:
        logger.error(f"Error getting translation history for {user_id}: {e}")
        embed = discord.Embed(
            title="❌ Error",
            description="Unable to retrieve translation history. Please try again later.",
            color=0xe74c3c
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    if not history:
        embed = discord.Embed(
            title="📚 Translation History",
            description="No translations found. Start translating to build your history!",
            color=0x95a5a6
        )
        
        embed.add_field(
            name="🚀 Start Translating",
            value="Use `/texttr`, `/voice`, or `/voicechat` to create your first translation!",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Get tier info for styling
    tier_info = tier_handler.get_tier_info(current_tier)
    
    embed = discord.Embed(
        title=f"📚 Your Translation History {tier_info['emoji']}",
        description=f"Showing your {len(history)} most recent translations",
        color=tier_info['color']
    )
    
    for i, translation in enumerate(history, 1):
        try:
            # Get language names and flags
            source_lang = translation.get('source_lang', 'unknown')
            target_lang = translation.get('target_lang', 'unknown')
            
            source_name = languages.get(source_lang, source_lang)
            target_name = languages.get(target_lang, target_lang)
            source_flag = flag_mapping.get(source_lang, '🌐')
            target_flag = flag_mapping.get(target_lang, '🌐')
            
            # Format the translation entry with proper field names
            original_text = translation.get('original', translation.get('original_text', 'N/A'))
            translated_text = translation.get('translated', translation.get('translated_text', 'N/A'))
            translation_type = translation.get('type', translation.get('translation_type', 'text'))
            
            # Truncate long text
            original_display = original_text[:80] + "..." if len(original_text) > 80 else original_text
            translated_display = translated_text[:80] + "..." if len(translated_text) > 80 else translated_text
            
            # Add timestamp if available
            timestamp_info = ""
            if 'created_at' in translation:
                try:
                    from datetime import datetime
                    created_at = datetime.fromisoformat(translation['created_at'])
                    timestamp_info = f" • <t:{int(created_at.timestamp())}:R>"
                except:
                    pass
            
            # Type emoji
            type_emoji = {
                'text': '📝',
                'voice': '🎤', 
                'auto': '🔄',
                'dm': '💬'
            }.get(translation_type, '📝')
            
            embed.add_field(
                name=f"{i}. {source_flag} {source_name} → {target_flag} {target_name} {type_emoji}{timestamp_info}",
                value=f"**Original:** {original_display}\n**Translation:** {translated_display}",
                inline=False
            )
            
        except Exception as e:
            logger.error(f"Error formatting translation {i}: {e}")
            embed.add_field(
                name=f"{i}. Translation Error",
                value="Unable to display this translation",
                inline=False
            )
    
    # Add tier-specific footer and info
    if current_tier == 'free':
        # Free user with temporary access
        embed.add_field(
            name="🎁 Temporary Access",
            value="You have temporary history access! Upgrade to Basic for permanent access.",
            inline=False
        )
        embed.set_footer(text="🆓 Free + Temp Access: Limited history • /upgrade to upgrade")
        
    elif current_tier == 'basic':
        embed.add_field(
            name="🥉 Basic Tier Benefits",
            value=f"• History access (up to {tier_limits['basic']} entries)\n• 500 character translations\n• Auto-translate feature",
            inline=False
        )
        embed.set_footer(text="🥉 Basic: Translation history included • /upgrade for more features")
        
    elif current_tier == 'premium':
        embed.add_field(
            name="🥈 Premium Tier Benefits", 
            value=f"• Extended history (up to {tier_limits['premium']} entries)\n• Priority processing\n• Enhanced voice features",
            inline=False
        )
        embed.set_footer(text="🥈 Premium: Extended history access • /upgrade for Pro features")
        
    else:  # Pro tier
        embed.add_field(
            name="🥇 Pro Tier Benefits",
            value=f"• Full history access (up to {tier_limits['pro']} entries)\n• Unlimited translations\n• Beta features & priority support",
            inline=False
        )
        embed.set_footer(text="🥇 Pro: Full history access • Thank you for your support!")
    
    # Add usage tip
    if len(history) >= limit:
        embed.add_field(
            name="💡 Tip",
            value=f"Showing maximum {limit} entries for your tier. Use a smaller number to see fewer results.",
            inline=False
        )
    
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
async def help_command(interaction: discord.Interaction):
    await track_command_usage(interaction)
    
    embed = discord.Embed(
        title="🤖 Muse Translator - Command List",
        description="Here are all available commands:",
        color=0x3498db
    )
    
    # Check if we're in server or user context
    is_server = interaction.guild is not None
    
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
    
    # Reward System Commands (NEW)
    embed.add_field(
        name="💎 Reward System",
        value=(
            "`/daily` - Claim daily point rewards\n"
            "`/shop` - Browse reward shop\n"
            "`/buy [reward]` - Purchase rewards with points\n"
            "`/profile [user]` - View profile and stats\n"
            "`/rewards` - View active rewards\n"
            "`/gift [user] [amount]` - Gift points to others"
        ),
        inline=False
    )
    
    # Leaderboard & Social Commands (NEW)
    embed.add_field(
        name="🏆 Social & Competition",
        value=(
            "`/leaderboard` - View top users by points\n"
            "`/achievements` - View your badges and achievements\n"
            "`/transactions` - View point transaction history"
        ),
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
            "`/history` - View translation history"
        ),
        inline=False
    )
    
    # Information Commands
    embed.add_field(
        name="ℹ️ Information",
        value=(
            "`/list` - Show all supported languages\n"
            "`/status` - Check your account status & rewards\n"
            "`/upgrade` - Get premium access info\n"
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
    
    # Add usage tips
    embed.add_field(
        name="💡 Usage Tips",
        value=(
            "• Use `auto` as source language for automatic detection\n"
            "• Language codes: `en`, `es`, `fr` or names: `English`, `Spanish`, `French`\n"
            "• Earn points daily and purchase temporary premium features!\n"
            "• Example: `/texttr text:'Hello' source_lang:en target_lang:es`"
        ),
        inline=False
    )
    
    # Add context-specific footer
    if is_server:
        embed.set_footer(text=f"Server Mode: {interaction.guild.name} | All features available | Use /daily for points!")
    else:
        embed.set_footer(text="User Mode: Perfect for DMs | Some features are server-only | Use /daily for points!")
    
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
    user_id = interaction.user.id
    
    # Validate rating
    if rating < 1 or rating > 5:
        await interaction.response.send_message(
            "❌ Rating must be between 1 and 5 stars!",
            ephemeral=True
        )
        return
    
    try:
        # Get user data to check sessions and last feedback
        user_data = reward_db.get_or_create_user(user_id, interaction.user.display_name)
        
        # Check if user has enough sessions (minimum 3 sessions to leave feedback)
        if user_data['total_sessions'] < 3:
            sessions_needed = 3 - user_data['total_sessions']
            await interaction.response.send_message(
                f"📊 You need **{sessions_needed} more translation sessions** before you can leave feedback!\n"
                f"💡 Try using `/texttr`, `/voice`, or `/voicechat` to build up your sessions.\n"
                f"Current sessions: **{user_data['total_sessions']}/3**",
                ephemeral=True
            )
            return
        
        # Check daily feedback limit
        from datetime import datetime, timedelta
        now = datetime.now()
        today = now.date().isoformat()
        
        # Get user's last feedback date
        last_feedback = await feedback_db.get_last_feedback_date(user_id)
        
        if last_feedback:
            last_feedback_date = datetime.fromisoformat(last_feedback).date()
            if last_feedback_date >= now.date():
                # Calculate time until next feedback allowed
                tomorrow = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                time_left = tomorrow - now
                hours_left = int(time_left.total_seconds() // 3600)
                minutes_left = int((time_left.total_seconds() % 3600) // 60)
                
                await interaction.response.send_message(
                    f"⏰ You can only leave feedback **once per day**!\n"
                    f"⏳ Next feedback available in: **{hours_left}h {minutes_left}m**\n"
                    f"📅 Come back tomorrow to share more feedback!",
                    ephemeral=True
                )
                return
        
        # Check session-based feedback (every 3 sessions since last feedback)
        last_feedback_session = await feedback_db.get_last_feedback_session(user_id)
        if last_feedback_session:
            sessions_since_feedback = user_data['total_sessions'] - last_feedback_session
            if sessions_since_feedback < 3:
                sessions_needed = 3 - sessions_since_feedback
                await interaction.response.send_message(
                    f"📈 You need **{sessions_needed} more sessions** since your last feedback!\n"
                    f"💡 Use the bot more and come back to share your updated experience.\n"
                    f"Sessions since last feedback: **{sessions_since_feedback}/3**",
                    ephemeral=True
                )
                return
        
        # Add feedback to database
        await feedback_db.add_feedback(
            user_id=user_id,
            username=interaction.user.display_name,
            rating=rating,
            message=message,
            session_count=user_data['total_sessions']  # Store session count when feedback was given
        )
        
        # Award points for feedback (tier-based rewards)
        current_tier = await tier_handler.get_user_tier_async(user_id)
        feedback_points = {
            'free': 15,
            'basic': 20,
            'premium': 25,
            'pro': 30
        }.get(current_tier, 15)
        
        # Bonus points for detailed feedback
        if message and len(message.strip()) >= 20:
            feedback_points += 10
            detailed_bonus = True
        else:
            detailed_bonus = False
        
        # Award points
        reward_db.add_points(
            user_id, 
            feedback_points, 
            f"Feedback submission ({rating}⭐)" + (" + detailed message bonus" if detailed_bonus else "")
        )
        
        # Create response
        stars = "⭐" * rating
        response_embed = discord.Embed(
            title="✅ Thank you for your feedback!",
            description=f"{stars} **{rating}/5 stars**",
            color=0x00ff00 if rating >= 4 else 0xff9900 if rating == 3 else 0xff6b6b
        )
        
        if message:
            response_embed.add_field(
                name="💬 Your Message",
                value=f"\"{message}\"",
                inline=False
            )
        
        # Points reward info
        points_text = f"💎 **+{feedback_points} points** earned!"
        if detailed_bonus:
            points_text += "\n🎁 **+10 bonus** for detailed feedback!"
        
        response_embed.add_field(
            name="🎁 Reward",
            value=points_text,
            inline=False
        )
        
        # Next feedback info
        response_embed.add_field(
            name="⏰ Next Feedback",
            value="Available tomorrow or after 3 more sessions",
            inline=False
        )
        
        response_embed.set_footer(text="Your feedback helps improve Muse for everyone! 💖")
        
        await interaction.response.send_message(embed=response_embed, ephemeral=True)
        
        # Send notification to feedback channel (optional)
        FEEDBACK_CHANNEL_ID = 1234567890123456789  # Replace with your channel ID
        feedback_channel = client.get_channel(FEEDBACK_CHANNEL_ID)
        
        if feedback_channel:
            notification_embed = discord.Embed(
                title="📝 New Feedback Received!",
                color=0x00ff00 if rating >= 4 else 0xff9900 if rating == 3 else 0xff6b6b
            )
            
            notification_embed.add_field(
                name="👤 User", 
                value=f"{interaction.user.display_name}\n`{user_id}`", 
                inline=True
            )
            notification_embed.add_field(
                name="⭐ Rating", 
                value=f"{stars} {rating}/5", 
                inline=True
            )
            notification_embed.add_field(
                name="📊 Sessions", 
                value=f"{user_data['total_sessions']} total", 
                inline=True
            )
            notification_embed.add_field(
                name="🌍 Context", 
                value=interaction.guild.name if interaction.guild else "DM", 
                inline=True
            )
            notification_embed.add_field(
                name="⭐ Tier", 
                value=current_tier.title(), 
                inline=True
            )
            notification_embed.add_field(
                name="💎 Points Awarded", 
                value=f"{feedback_points} points", 
                inline=True
            )
            
            if message:
                notification_embed.add_field(
                    name="💬 Message", 
                    value=message[:1000] + ("..." if len(message) > 1000 else ""), 
                    inline=False
                )
            
            notification_embed.timestamp = datetime.now()
            
            await feedback_channel.send(embed=notification_embed)
        
        # Track achievement for feedback
        await reward_db.award_achievement(user_id, 'feedback_provider')
        
    except Exception as e:
        logger.error(f"Error in feedback command: {e}")
        await interaction.response.send_message(
            f"❌ Error saving feedback: {str(e)}\n"
            "Please try again later or contact support.",
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
@tree.command(name="daily", description="Claim your daily point reward")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def daily_reward(interaction: discord.Interaction):
    await track_command_usage(interaction)
    
    user_id = interaction.user.id
    username = interaction.user.display_name
    is_premium = user_id in tier_handler.premium_users
    
    result = reward_db.claim_daily_reward(user_id, username, is_premium)
    
    if result['success']:
        embed = discord.Embed(
            title="🎁 Daily Reward Claimed!",
            description=f"You earned **{result['points_earned']} points**!",
            color=0xf1c40f if is_premium else 0x2ecc71
        )
        
        embed.add_field(
            name="💎 Total Points",
            value=f"{result['total_points']:,}",
            inline=True
        )
        
        embed.add_field(
            name="⭐ Tier",
            value="Premium" if is_premium else "Free",
            inline=True
        )
        
        embed.add_field(
            name="⏰ Next Claim",
            value="Tomorrow",
            inline=True
        )
        
        if not is_premium:
            embed.add_field(
                name="💡 Tip",
                value="Premium users get 2.5x daily rewards! Use `/upgrade` to upgrade.",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        embed = discord.Embed(
            title="❌ Daily Reward",
            description=result['error'],
            color=0xe74c3c
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="shop", description="Browse and purchase rewards with points")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def shop(interaction: discord.Interaction):
    await track_command_usage(interaction)
    
    user_data = reward_db.get_or_create_user(interaction.user.id, interaction.user.display_name)
    
    embed = discord.Embed(
        title="🛍️ Reward Shop",
        description=f"Your Points: **{user_data['points']:,}** 💎",
        color=0x3498db
    )
    
    for reward_id, reward in REWARDS.items():
        status = ""
        if reward_db.has_active_reward(interaction.user.id, reward['type']):
            status = " ✅ *Active*"
        elif user_data['points'] < reward['cost']:
            status = " ❌ *Not enough points*"
        
        embed.add_field(
            name=f"{reward['name']} - {reward['cost']} 💎{status}",
            value=f"{reward['description']}\nDuration: {reward['duration_hours']}h",
            inline=False
        )
    
    embed.set_footer(text="Use /buy [reward_name] to purchase • Points refresh daily with /daily")
    
    await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="buy", description="Purchase a reward with points")
@app_commands.describe(reward="The reward you want to purchase")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def buy_reward(interaction: discord.Interaction, reward: str):
    await track_command_usage(interaction)
    
    # Find reward by name or ID
    reward_id = None
    for r_id, r_data in REWARDS.items():
        if (reward.lower() in r_data['name'].lower() or 
            reward.lower() == r_id.lower()):
            reward_id = r_id
            break
    
    if not reward_id:
        embed = discord.Embed(
            title="❌ Invalid Reward",
            description=f"Reward '{reward}' not found. Use `/shop` to see available rewards.",
            color=0xe74c3c
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    result = reward_db.purchase_reward(interaction.user.id, reward_id)
    
    if result['success']:
        reward_data = result['reward']
        expires_at = result['expires_at']
        
        embed = discord.Embed(
            title="✅ Purchase Successful!",
            description=f"You purchased **{reward_data['name']}**!",
            color=0x2ecc71
        )
        
        embed.add_field(
            name="💎 Points Spent",
            value=f"{reward_data['cost']:,}",
            inline=True
        )
        
        embed.add_field(
            name="💰 Points Remaining",
            value=f"{result['points_remaining']:,}",
            inline=True
        )
        
        embed.add_field(
            name="⏰ Expires",
            value=f"<t:{int(expires_at.timestamp())}:R>",
            inline=True
        )
        
        embed.add_field(
            name="📝 Description",
            value=reward_data['description'],
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    else:
        embed = discord.Embed(
            title="❌ Purchase Failed",
            description=result['error'],
            color=0xe74c3c
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
    
    top_users = reward_db.get_leaderboard(10)
    user_rank = reward_db.get_user_rank(interaction.user.id)
    
    embed = discord.Embed(
        title="🏆 Leaderboard - Top Users",
        description="Top 10 users by total points",
        color=0xf1c40f
    )
    
    if not top_users:
        embed.description = "No users found!"
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    leaderboard_text = ""
    for i, user_data in enumerate(top_users, 1):
        # Get rank emoji
        if i == 1:
            rank_emoji = "🥇"
        elif i == 2:
            rank_emoji = "🥈"
        elif i == 3:
            rank_emoji = "🥉"
        else:
            rank_emoji = f"{i}."
        
        # Highlight current user
        highlight = "**" if user_data['user_id'] == interaction.user.id else ""
        
        leaderboard_text += f"{rank_emoji} {highlight}{user_data['username']}{highlight} - {user_data['points']:,} 💎\n"
    
    embed.add_field(
        name="Top Users",
        value=leaderboard_text,
        inline=False
    )
    
    # Show user's rank if not in top 10
    if user_rank and user_rank > 10:
        embed.add_field(
            name="Your Rank",
            value=f"#{user_rank}",
            inline=True
        )
    
    # Add statistics
    total_users = reward_db.get_total_users()
    total_points = reward_db.get_total_points_distributed()
    
    embed.add_field(
        name="📊 Statistics",
        value=f"Total Users: {total_users:,}\nTotal Points Distributed: {total_points:,}",
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
        
        # Get user data from reward system
        user_data = reward_db.get_or_create_user(user_id, username)
        achievements = reward_db.get_user_achievements(user_id)
        
        # Get user limits and tier info (fix async call)
        try:
            if hasattr(tier_handler.get_limits, '__call__') and asyncio.iscoroutinefunction(tier_handler.get_limits):
                limits = await tier_handler.get_limits(user_id)
            else:
                limits = tier_handler.get_limits(user_id)
        except Exception as e:
            logger.error(f"Error getting limits: {e}")
            # Fallback limits
            limits = {'text_limit': 100, 'voice_limit': 30}
        
        is_premium = user_id in tier_handler.premium_users
        
        # Get rank information safely
        try:
            rank_info = get_rank_from_points(user_data['points'])
        except Exception as e:
            logger.error(f"Error getting rank: {e}")
            rank_info = {'name': '🆕 Newcomer', 'emoji': '🆕', 'color': 0x95a5a6}
        
        # Calculate usage statistics safely
        total_translations = user_data.get('total_translations', 0)
        total_sessions = user_data.get('total_sessions', 0)
        total_usage_hours = user_data.get('total_usage_hours', 0.0)
        languages_used = user_data.get('languages_used', [])
        
        # Get daily usage if available
        try:
            if hasattr(usage_tracker, 'get_remaining_time'):
                if asyncio.iscoroutinefunction(usage_tracker.get_remaining_time):
                    remaining_time = await usage_tracker.get_remaining_time(user_id, is_premium)
                else:
                    remaining_time = usage_tracker.get_remaining_time(user_id, is_premium)
            else:
                remaining_time = "N/A"
        except Exception as e:
            logger.error(f"Error getting remaining time: {e}")
            remaining_time = "N/A"
        
        # Create main profile embed
        embed = discord.Embed(
            title=f"👤 {username}'s Translation Profile",
            color=rank_info.get('color', 0x3498db)
        )
        
        # Add user avatar if available
        if interaction.user.avatar:
            embed.set_thumbnail(url=interaction.user.avatar.url)
        
        # Rank and Points Section
        embed.add_field(
            name="🏆 Rank & Status",
            value=(
                f"{rank_info.get('emoji', '🆕')} **{rank_info.get('name', 'Newcomer')}**\n"
                f"💎 **{user_data.get('points', 0):,}** points\n"
                f"{'⭐ Premium Member' if is_premium else '🆓 Free Tier'}"
            ),
            inline=True
        )
        
        # Usage Statistics
        embed.add_field(
            name="📊 Usage Statistics",
            value=(
                f"📝 **{total_translations:,}** translations\n"
                f"🎤 **{total_sessions:,}** voice sessions\n"
                f"⏱️ **{total_usage_hours:.1f}** hours used\n"
                f"🌍 **{len(languages_used)}** languages"
            ),
            inline=True
        )
        
        # Current Limits - handle potential infinity values
        try:
            text_limit_display = "Unlimited" if limits.get('text_limit') == float('inf') else f"{limits.get('text_limit', 100):,} chars"
            voice_limit_display = "Unlimited" if limits.get('voice_limit') == float('inf') else f"{limits.get('voice_limit', 30)} min"
        except Exception as e:
            logger.error(f"Error formatting limits: {e}")
            text_limit_display = "100 chars"
            voice_limit_display = "30 min"
        
        # Format remaining time safely
        try:
            if isinstance(remaining_time, (int, float)) and remaining_time != float('inf'):
                remaining_display = f"{int(remaining_time/60)} min remaining today"
            elif remaining_time == float('inf'):
                remaining_display = "Unlimited"
            else:
                remaining_display = "N/A"
        except Exception as e:
            logger.error(f"Error formatting remaining time: {e}")
            remaining_display = "N/A"
        
        embed.add_field(
            name="⚙️ Current Limits",
            value=(
                f"📝 Text: **{text_limit_display}**\n"
                f"🎤 Voice: **{voice_limit_display}**\n"
                f"📅 Today: **{remaining_display}**"
            ),
            inline=True
        )
        
        # Achievement Progress
        total_achievements = 12  # Total number of achievements available
        achievement_count = len(achievements) if achievements else 0
        achievement_percentage = int((achievement_count / total_achievements) * 100) if total_achievements > 0 else 0
        
        # Get badges safely
        try:
            badges = reward_db.get_user_badges(user_id, achievements, user_data.get('points', 0))
            badge_count = len(badges) if badges else 0
        except Exception as e:
            logger.error(f"Error getting badges: {e}")
            badge_count = 0
        
        embed.add_field(
            name="🎯 Achievement Progress",
            value=(
                f"🏅 **{achievement_count}/{total_achievements}** unlocked\n"
                f"📈 **{achievement_percentage}%** complete\n"
                f"🎖️ **{badge_count}** badges earned"
            ),
            inline=True
        )
        
        # Most Used Languages (top 5)
        if languages_used:
            language_display = []
            for lang_code in languages_used[:5]:  # Show top 5
                try:
                    lang_name = languages.get(lang_code, lang_code)
                    flag = flag_mapping.get(lang_code, '🌐')
                    language_display.append(f"{flag} {lang_name}")
                except Exception as e:
                    logger.error(f"Error formatting language {lang_code}: {e}")
                    language_display.append(f"🌐 {lang_code}")
            
            embed.add_field(
                name="🌍 Languages Used",
                value="\n".join(language_display),
                inline=True
            )
        else:
            embed.add_field(
                name="🌍 Languages Used",
                value="None yet - start translating!",
                inline=True
            )
        
        # Recent Activity Summary
        recent_activity = []
        if total_translations > 0:
            recent_activity.append(f"📝 Translations: {total_translations}")
        if total_sessions > 0:
            recent_activity.append(f"🎤 Voice sessions: {total_sessions}")
        
        # Handle daily claim safely
        try:
            last_claim = user_data.get('last_daily_claim')
            if last_claim:
                try:
                    last_claim_dt = datetime.fromisoformat(last_claim)
                    days_ago = (datetime.now() - last_claim_dt).days
                    if days_ago == 0:
                        recent_activity.append("🎁 Daily reward: Claimed today")
                    elif days_ago == 1:
                        recent_activity.append("🎁 Daily reward: Available")
                    else:
                        recent_activity.append(f"🎁 Daily reward: {days_ago} days ago")
                except Exception:
                    recent_activity.append("🎁 Daily reward: Available")
            else:
                recent_activity.append("🎁 Daily reward: Available")
        except Exception as e:
            logger.error(f"Error handling daily claim: {e}")
            recent_activity.append("🎁 Daily reward: Available")
        
        embed.add_field(
            name="📅 Recent Activity",
            value="\n".join(recent_activity) if recent_activity else "No recent activity",
            inline=True
        )
        
        # Active Rewards/Boosts - handle safely
        active_rewards = []
        try:
            if hasattr(reward_db, 'has_active_reward'):
                if reward_db.has_active_reward(user_id, 'unlimited_text'):
                    active_rewards.append("📝 Unlimited Text")
                if reward_db.has_active_reward(user_id, 'unlimited_voice'):
                    active_rewards.append("🎤 Unlimited Voice")
                if reward_db.has_active_reward(user_id, 'enhanced_voice_1day'):
                    active_rewards.append("🚀 Enhanced Voice (1 day)")
                if reward_db.has_active_reward(user_id, 'enhanced_voice_7day'):
                    active_rewards.append("🚀 Enhanced Voice (7 days)")
                if reward_db.has_active_reward(user_id, 'double_points'):
                    active_rewards.append("💎 Double Points")
        except Exception as e:
            logger.error(f"Error checking active rewards: {e}")
        
        if active_rewards:
            embed.add_field(
                name="🎁 Active Rewards",
                value="\n".join(active_rewards),
                inline=True
            )
        
         # Add progress to next rank - FIXED VERSION
        try:
            # Ensure RANK_BADGES is defined
            if 'RANK_BADGES' not in globals():
                global RANK_BADGES
                RANK_BADGES = {
                    0: {'name': '🆕 Newcomer', 'emoji': '🆕', 'color': 0x95a5a6},
                    50: {'name': '🌱 Beginner', 'emoji': '🌱', 'color': 0x2ecc71},
                    150: {'name': '📈 Learner', 'emoji': '📈', 'color': 0x3498db},
                    300: {'name': '🎯 Dedicated', 'emoji': '🎯', 'color': 0x9b59b6},
                    500: {'name': '⭐ Expert', 'emoji': '⭐', 'color': 0xf1c40f},
                    1000: {'name': '👑 Master', 'emoji': '👑', 'color': 0xe67e22},
                    2000: {'name': '🏆 Legend', 'emoji': '🏆', 'color': 0xe74c3c},
                    5000: {'name': '💎 Grandmaster', 'emoji': '💎', 'color': 0x1abc9c}
                }
            
            next_rank_info = None
            points_needed = 0
            current_points = user_data.get('points', 0)
            
            # Find the next rank
            for min_points in sorted(RANK_BADGES.keys()):
                if current_points < min_points:
                    next_rank_info = RANK_BADGES[min_points]
                    points_needed = min_points - current_points
                    break
            
            # Only add the field if there's a next rank to achieve
            if next_rank_info and points_needed > 0:
                # Safely get the name and emoji with fallbacks
                next_name = next_rank_info.get('name', 'Unknown Rank')
                next_emoji = next_rank_info.get('emoji', '🎯')
                
                embed.add_field(
                    name="📈 Next Rank Progress",
                    value=(
                        f"{next_emoji} **{next_name}**\n"
                        f"Need **{points_needed:,}** more points"
                    ),
                    inline=True
                )
            else:
                # User has reached the highest rank
                embed.add_field(
                    name="📈 Rank Status",
                    value="🏆 **Maximum rank achieved!**\nCongratulations!",
                    inline=True
                )
                
        except Exception as e:
            logger.error(f"Error calculating next rank: {e}")
            # Add a safe fallback field
            embed.add_field(
                name="📈 Rank Progress",
                value="Keep translating to unlock new ranks!",
                inline=True
            )

        
        # Add footer with context info
        if interaction.guild:
            embed.set_footer(
                text=f"Server: {interaction.guild.name} • Use /achievements for detailed progress",
                icon_url=interaction.guild.icon.url if interaction.guild.icon else None
            )
        else:
            embed.set_footer(text="📱 User Profile • Use /achievements for detailed progress")
        
        # Create view with action buttons
        view = ProfileView(user_id, is_premium)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
    except Exception as e:
        logger.error(f"Profile command error: {e}")
        await interaction.response.send_message(
            "❌ An error occurred while loading your profile. Please try again later.",
            ephemeral=True
        )

class ProfileView(discord.ui.View):
    def __init__(self, user_id: int, is_premium: bool):
        super().__init__(timeout=300)
        self.user_id = user_id
        self.is_premium = is_premium

    @discord.ui.button(label="🎯 Achievements", style=discord.ButtonStyle.primary)
    async def view_achievements(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Redirect to achievements command safely
        try:
            # Call the achievements function directly instead of the command
            user_data = reward_db.get_or_create_user(self.user_id, interaction.user.display_name)
            achievements = reward_db.get_user_achievements(self.user_id)
            
            embed = discord.Embed(
                title=f"🏆 {interaction.user.display_name}'s Achievements",
                description="Your achievement progress:",
                color=0xf1c40f
            )
            
            embed.add_field(
                name="🎯 Quick Stats",
                value=(
                    f"**Achievements:** {len(achievements)}/12 unlocked\n"
                    f"**Points:** {user_data.get('points', 0):,}\n"
                    f"**Translations:** {user_data.get('total_translations', 0):,}"
                ),
                inline=False
            )
            
            if achievements:
                recent_text = ""
                for ach in achievements[-3:]:  # Last 3 achievements
                    recent_text += f"🏅 {ach}\n"
                embed.add_field(
                    name="🎉 Recent Achievements",
                    value=recent_text,
                    inline=False
                )
            
            embed.add_field(
                name="💡 Tip",
                value="Use `/achievements` for the full interactive achievement system!",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Achievements redirect error: {e}")
            await interaction.response.send_message("❌ Error loading achievements. Use `/achievements` command directly.", ephemeral=True)

    @discord.ui.button(label="🛍️ Rewards Shop", style=discord.ButtonStyle.success)
    async def rewards_shop(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Simple shop preview instead of full redirect
            user_data = reward_db.get_or_create_user(self.user_id, interaction.user.display_name)
            
            embed = discord.Embed(
                title="🛍️ Rewards Shop Preview",
                description=f"Your current points: **{user_data.get('points', 0):,}**",
                color=0x2ecc71
            )
            
            embed.add_field(
                name="🛒 Available Items",
                value=(
                    "🎤 **Enhanced Voice (1 day)** - 100 pts\n"
                    "📝 **Unlimited Text (1 day)** - 150 pts\n"
                    "💎 **Double Points (1 day)** - 200 pts\n"
                    "🚀 **Enhanced Voice (7 days)** - 500 pts"
                ),
                inline=False
            )
            
            embed.add_field(
                name="💡 How to Shop",
                value="Use `/shop` command for the full interactive shopping experience!",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)

            
        except Exception as e:
            logger.error(f"Shop redirect error: {e}")
            await interaction.response.send_message("❌ Error loading shop. Use `/shop` command directly.", ephemeral=True)

    @discord.ui.button(label="🎁 Daily Reward", style=discord.ButtonStyle.secondary)
    async def daily_reward(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Simple daily reward check instead of full redirect
            user_data = reward_db.get_or_create_user(self.user_id, interaction.user.display_name)
            
            # Check if daily reward is available
            last_claim = user_data.get('last_daily_claim')
            can_claim = True
            
            if last_claim:
                try:
                    last_claim_dt = datetime.fromisoformat(last_claim)
                    if (datetime.now() - last_claim_dt).days < 1:
                        can_claim = False
                        next_claim = last_claim_dt + timedelta(days=1)
                        hours_left = int((next_claim - datetime.now()).total_seconds() / 3600)
                except Exception:
                    can_claim = True
            
            if can_claim:
                embed = discord.Embed(
                    title="🎁 Daily Reward Available!",
                    description="Use `/daily` command to claim your daily reward!",
                    color=0x2ecc71
                )
                
                embed.add_field(
                    name="💎 Reward",
                    value="**10-50 points** + bonus for streaks!",
                    inline=False
                )
            else:
                embed = discord.Embed(
                    title="🎁 Daily Reward",
                    description=f"Next reward available in **{hours_left}** hours",
                    color=0x95a5a6
                )
                
                embed.add_field(
                    name="📊 Current Streak",
                    value=f"**{user_data.get('daily_streak', 0)}** days",
                    inline=False
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Daily reward redirect error: {e}")
            await interaction.response.send_message("❌ Error checking daily reward. Use `/daily` command directly.", ephemeral=True)

    @discord.ui.button(label="📊 Detailed Stats", style=discord.ButtonStyle.secondary)
    async def detailed_stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            user_data = reward_db.get_or_create_user(self.user_id, interaction.user.display_name)
            
            embed = discord.Embed(
                title="📊 Detailed Statistics",
                description=f"Complete stats for {interaction.user.display_name}",
                color=0x3498db
            )
            
            # Translation Statistics
            embed.add_field(
                name="📝 Translation Stats",
                value=(
                    f"**Total Translations:** {user_data.get('total_translations', 0):,}\n"
                    f"**Text Translations:** {user_data.get('text_translations', 0):,}\n"
                    f"**Voice Translations:** {user_data.get('voice_translations', 0):,}\n"
                    f"**Auto Translations:** {user_data.get('auto_translations', 0):,}"
                ),
                inline=False
            )
            
            # Usage Statistics
            total_hours = user_data.get('total_usage_hours', 0.0)
            total_sessions = user_data.get('total_sessions', 0)
            avg_session = total_hours / max(total_sessions, 1)
            
            embed.add_field(
                name="⏱️ Usage Stats",
                value=(
                    f"**Total Usage Time:** {total_hours:.1f} hours\n"
                    f"**Total Sessions:** {total_sessions:,}\n"
                    f"**Average Session:** {avg_session:.1f} hours\n"
                    f"**Commands Used:** {user_data.get('commands_used', 0):,}"
                ),
                inline=False
            )
            
            # Language Statistics
            languages_used = user_data.get('languages_used', [])
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
            embed.add_field(
                name="💎 Points & Rewards",
                value=(
                    f"**Current Points:** {user_data.get('points', 0):,}\n"
                    f"**Total Points Earned:** {user_data.get('total_points_earned', user_data.get('points', 0)):,}\n"
                    f"**Points Spent:** {user_data.get('points_spent', 0):,}\n"
                    f"**Daily Streak:** {user_data.get('daily_streak', 0)} days"
                ),
                inline=False
            )
            
            # Account Information
            created_date = user_data.get('created_at', 'Unknown')
            if created_date != 'Unknown':
                try:
                    created_dt = datetime.fromisoformat(created_date)
                    days_active = (datetime.now() - created_dt).days
                    embed.add_field(
                        name="📅 Account Info",
                        value=(
                            f"**Member Since:** {created_dt.strftime('%B %d, %Y')}\n"
                            f"**Days Active:** {days_active}\n"
                            f"**Account Type:** {'Premium ⭐' if self.is_premium else 'Free 🆓'}"
                        ),
                        inline=False
                    )
                except Exception as e:
                    logger.error(f"Error parsing created_at: {e}")
            
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
            
            # Usage Preferences
            most_used_lang = "None"
            if user_data.get('languages_used'):
                try:
                    most_used_code = user_data['languages_used'][0]
                    most_used_lang = languages.get(most_used_code, most_used_code)
                except Exception:
                    most_used_lang = "None"
            
            embed.add_field(
                name="📊 Usage Statistics",
                value=(
                    f"**Total Commands:** {user_data.get('commands_used', 0):,}\n"
                    f"**Favorite Feature:** {'Voice Chat' if user_data.get('voice_translations', 0) > user_data.get('text_translations', 0) else 'Text Translation'}\n"
                    f"**Most Used Language:** {most_used_lang}"
                ),
                inline=False
            )
            
            # Quick Actions
            embed.add_field(
                name="🚀 Quick Actions",
                value=(
                    "Use the buttons below to:\n"
                    "• Toggle text visibility settings\n"
                    "• Manage auto-translation\n"
                    "• View premium options\n"
                    "• Reset preferences"
                ),
                inline=False
            )
            
            # Privacy Information
            embed.add_field(
                name="🔒 Privacy & Data",
                value=(
                    "• Your translation data is not stored\n"
                    "• Only usage statistics are tracked\n"
                    "• Use `/stop` to end all sessions\n"
                    "• Data is used only for features & improvements"
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
                button.label = "🙈 Hide Original Text"
            else:
                hidden_sessions.add(self.user_id)
                status = "✅ Original text will now be **hidden** in translations"
                button.label = "👁️ Show Original Text"
            
            embed = discord.Embed(
                title="👁️ Text Visibility Updated",
                description=status,
                color=0x2ecc71
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
                source_lang = settings['source']
                target_lang = settings['target']
                
                source_name = "Auto-detect" if source_lang == "auto" else languages.get(source_lang, source_lang)
                target_name = languages.get(target_lang, target_lang)
                source_flag = '🔍' if source_lang == "auto" else flag_mapping.get(source_lang, '🌐')
                target_flag = flag_mapping.get(target_lang, '🌐')
                
                embed = discord.Embed(
                    title="🔄 Auto-Translation Active",
                    description=(
                        f"Currently translating from {source_flag} **{source_name}** "
                        f"to {target_flag} **{target_name}**\n\n"
                        f"Use `/stop` to disable auto-translation."
                    ),
                    color=0x3498db
                )
            else:
                embed = discord.Embed(
                    title="🔄 Auto-Translation Inactive",
                    description=(
                        "Auto-translation is currently disabled.\n\n"
                        "Use `/autotranslate [source] [target]` to enable automatic "
                        "translation of all your messages."
                    ),
                    color=0x95a5a6
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
                    title="⭐ Premium Member",
                    description="Thank you for supporting Muse! You have access to all premium features.",
                    color=0xf1c40f
                )
                
                embed.add_field(
                    name="✨ Your Premium Benefits",
                    value=(
                        "• ♾️ Unlimited text translation\n"
                        "• 🎤 Extended voice translation time\n"
                        "• 💎 Double points for all activities\n"
                        "• 🚀 Access to Enhanced Voice V2\n"
                        "• 🎯 Priority support\n"
                        "• 🏆 Premium badge & rank bonuses"
                    ),
                    inline=False
                )
                
                embed.add_field(
                    name="💝 Thank You!",
                    value="Your support helps us improve Muse for everyone!",
                    inline=False
                )
            else:
                embed = discord.Embed(
                    title="⭐ Upgrade to Premium",
                    description="Unlock unlimited features for just $1/month!",
                    color=0x29abe0
                )
                
                embed.add_field(
                    name="🚀 Premium Benefits",
                    value=(
                        "• ♾️ Unlimited text translation\n"
                        "• 🎤 5-minute voice translation sessions\n"
                        "• 💎 Double points for all activities\n"
                        "• 🚀 Access to Enhanced Voice V2\n"
                        "• 🎯 Priority support\n"
                        "• 🏆 Premium badge & exclusive ranks"
                    ),
                    inline=False
                )
                
                embed.add_field(
                    name="💰 Just $1/Month",
                    value="Support Muse development and get unlimited access!",
                    inline=False
                )
                
                # Add Ko-fi button
                view = discord.ui.View()
                view.add_item(discord.ui.Button(
                    label="Subscribe on Ko-fi",
                    url="https://ko-fi.com/muse/tiers",
                    style=discord.ButtonStyle.link
                ))
                
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
                return
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Premium info error: {e}")
            await interaction.response.send_message("❌ Error loading premium information.", ephemeral=True)

    @discord.ui.button(label="🗑️ Reset Data", style=discord.ButtonStyle.danger)
    async def reset_data(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            embed = discord.Embed(
                title="⚠️ Reset User Data",
                description=(
                    "This will reset your:\n"
                    "• Text visibility preferences\n"
                    "• Auto-translation settings\n"
                    "• Active translation sessions\n\n"
                    "**Note:** Your points, achievements, and statistics will NOT be reset.\n"
                    "Are you sure you want to continue?"
                ),
                color=0xe74c3c
            )
            
            # Create confirmation view
            confirm_view = ResetConfirmView(self.user_id)
            
            await interaction.response.send_message(embed=embed, view=confirm_view, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Reset data error: {e}")
            await interaction.response.send_message("❌ Error initiating data reset.", ephemeral=True)

class ResetConfirmView(discord.ui.View):
    def __init__(self, user_id: int):
        super().__init__(timeout=60)
        self.user_id = user_id

    @discord.ui.button(label="✅ Confirm Reset", style=discord.ButtonStyle.danger)
    async def confirm_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            # Reset user preferences (not statistics/points)
            hidden_sessions.discard(self.user_id)
            if self.user_id in auto_translate_users:
                del auto_translate_users[self.user_id]
            
            # Stop any active sessions
            guild_id = interaction.guild_id
            if guild_id and guild_id in voice_translation_sessions:
                session = voice_translation_sessions[guild_id]
                try:
                    if session['voice_client'].is_listening():
                        session['voice_client'].stop_listening()
                    if 'sink' in session:
                        session['sink'].cleanup()
                    if session['voice_client'].is_connected():
                        await session['voice_client'].disconnect()
                    del voice_translation_sessions[guild_id]
                except Exception as e:
                    logger.error(f"Error stopping voice session: {e}")
            
            embed = discord.Embed(
                title="✅ Data Reset Complete",
                description=(
                    "Your preferences have been reset:\n"
                    "• Text visibility: Restored to default (show original)\n"
                    "• Auto-translation: Disabled\n"
                    "• Active sessions: Stopped\n\n"
                    "Your points, achievements, and statistics remain unchanged."
                ),
                color=0x2ecc71
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            
        except Exception as e:
            logger.error(f"Confirm reset error: {e}")
            await interaction.response.send_message("❌ Error resetting data.", ephemeral=True)

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.secondary)
    async def cancel_reset(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="❌ Reset Cancelled",
            description="No changes were made to your data.",
            color=0x95a5a6
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

@tree.command(name="gift", description="Gift points to another user")
@app_commands.describe(
    user="The user to gift points to",
    amount="Amount of points to gift (1-50 per day)"
)
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def gift_points(interaction: discord.Interaction, user: discord.User, amount: int):
    await track_command_usage(interaction)
    
    sender_id = interaction.user.id
    receiver_id = user.id
    
    # Validation
    if sender_id == receiver_id:
        await interaction.response.send_message("❌ You can't gift points to yourself!", ephemeral=True)
        return
    
    if amount < 1 or amount > 50:
        await interaction.response.send_message("❌ You can only gift 1-50 points at a time!", ephemeral=True)
        return
    
    # Check daily gift limit
    today = datetime.now().date()
    daily_gifted = reward_db.get_daily_gifted(sender_id, today)
    daily_limit = 100 if sender_id in tier_handler.premium_users else 25
    
    if daily_gifted + amount > daily_limit:
        remaining = daily_limit - daily_gifted
        embed = discord.Embed(
            title="❌ Daily Gift Limit Reached",
            description=f"You can only gift {daily_limit} points per day.\nYou have {remaining} points left to gift today.",
            color=0xe74c3c
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    # Check if sender has enough points
    sender_data = reward_db.get_or_create_user(sender_id, interaction.user.display_name)
    if sender_data['points'] < amount:
        embed = discord.Embed(
            title="❌ Insufficient Points",
            description=f"You need {amount} points but only have {sender_data['points']} points.",
            color=0xe74c3c
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    # Perform the transfer
    success = reward_db.transfer_points(
        sender_id, 
        receiver_id, 
        amount, 
        f"Gift from {interaction.user.display_name}"
    )
    
    if success:
        # Record daily gift
        reward_db.record_daily_gift(sender_id, amount, today)
        
        embed = discord.Embed(
            title="🎁 Gift Sent Successfully!",
            description=f"You gifted **{amount} points** to {user.display_name}!",
            color=0x2ecc71
        )
        
        embed.add_field(
            name="💎 Your Remaining Points",
            value=f"{sender_data['points'] - amount:,}",
            inline=True
        )
        
        embed.add_field(
            name="📊 Daily Gifts Used",
            value=f"{daily_gifted + amount}/{daily_limit}",
            inline=True
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
        
        # Try to notify the receiver
        try:
            receiver_embed = discord.Embed(
                title="🎁 You Received a Gift!",
                description=f"{interaction.user.display_name} gifted you **{amount} points**!",
                color=0x2ecc71
            )
            await user.send(embed=receiver_embed)
        except:
            pass  # User has DMs disabled
    else:
        embed = discord.Embed(
            title="❌ Gift Failed",
            description="Failed to transfer points. Please try again.",
            color=0xe74c3c
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
@tree.command(name="rewards", description="View your active rewards and their expiration times")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def active_rewards(interaction: discord.Interaction):
    await track_command_usage(interaction)
    
    user_id = interaction.user.id
    active_rewards = reward_db.get_active_rewards(user_id)
    
    embed = discord.Embed(
        title="🎁 Your Active Rewards",
        color=0x3498db
    )
    
    if not active_rewards:
        embed.description = "You don't have any active rewards.\nUse `/shop` to browse available rewards!"
        embed.add_field(
            name="💡 Tip",
            value="Claim your daily points with `/daily` to earn rewards!",
            inline=False
        )
    else:
        for reward in active_rewards:
            expires_timestamp = int(datetime.fromisoformat(reward['expires_at']).timestamp())
            
            embed.add_field(
                name=f"✨ {reward['name']}",
                value=f"Expires: <t:{expires_timestamp}:R>\n(<t:{expires_timestamp}:f>)",
                inline=False
            )
    
    # Show permanent benefits for premium users
    if user_id in tier_handler.premium_users:
        embed.add_field(
            name="⭐ Premium Benefits (Permanent)",
            value="• 2.5x daily rewards\n• 10x usage point multiplier\n• Enhanced Voice Chat V2 access",
            inline=False
        )
    
    await interaction.response.send_message(embed=embed, ephemeral=True)
@tree.command(name="transactions", description="View your recent point transactions")
@app_commands.allowed_installs(guilds=True, users=True)
@app_commands.allowed_contexts(guilds=True, dms=True, private_channels=True)
async def transactions(interaction: discord.Interaction):
    await track_command_usage(interaction)
    
    user_id = interaction.user.id
    transactions = reward_db.get_point_transactions(user_id, 15)
    
    embed = discord.Embed(
        title="💳 Recent Transactions",
        description="Your last 15 point transactions",
        color=0x3498db
    )
    
    if not transactions:
        embed.description = "No transactions found."
        await interaction.response.send_message(embed=embed, ephemeral=True)
        return
    
    transaction_text = ""
    for transaction in transactions:
        # Format amount with + or - sign
        amount_str = f"+{transaction['amount']}" if transaction['amount'] > 0 else str(transaction['amount'])
        
        # Get emoji based on transaction type
        type_emoji = {
            'earned': '💰',
            'daily': '🎁',
            'spent': '🛍️',
            'transfer_in': '📥',
            'transfer_out': '📤'
        }.get(transaction['type'], '💎')
        
        # Format timestamp
        try:
            timestamp = datetime.fromisoformat(transaction['timestamp'])
            time_str = timestamp.strftime("%m/%d %H:%M")
        except:
            time_str = "Unknown"
        
        transaction_text += f"{type_emoji} {amount_str} - {transaction['description']} ({time_str})\n"
    
    embed.add_field(
        name="Transaction History",
        value=transaction_text[:1024],  # Discord field limit
        inline=False
    )
    
    # Add current balance
    user_data = reward_db.get_or_create_user(user_id, interaction.user.display_name)
    embed.add_field(
        name="💎 Current Balance",
        value=f"{user_data['points']:,} points",
        inline=True
    )
    
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

@tree.command(name="removebasic", description="[ADMIN] Remove Basic tier access from any Discord user", guild=discord.Object(id=YOUR_SERVER_ID))
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
        current_tier = await tier_handler.get_user_tier_async(user.id)
        if current_tier != 'basic':
            await interaction.response.send_message(
                f"❌ User {user.display_name} doesn't have Basic tier! Current tier: {current_tier.title()}",
                ephemeral=True
            )
            return
        
        # Get expiration info before removal
        expires_at = await tier_handler.get_tier_expiration(user.id)
        
        # Remove Basic tier (downgrade to free)
        await tier_handler.downgrade_user_tier(user.id, reason)
        
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
        
        if expires_at:
            embed.description += f"**Was set to expire:** {expires_at.strftime('%Y-%m-%d %H:%M UTC')}\n"
        
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
        await interaction.response.send_message(f"❌ Error removing Basic tier: {str(e)}", ephemeral=True)


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

@tree.command(name="removepremium", description="[ADMIN] Remove Premium tier access from any Discord user", guild=discord.Object(id=YOUR_SERVER_ID))
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
        current_tier = await tier_handler.get_user_tier_async(user.id)
        if current_tier != 'premium':
            await interaction.response.send_message(
                f"❌ User {user.display_name} doesn't have Premium tier! Current tier: {current_tier.title()}",
                ephemeral=True)
            return
                # Get expiration info before removal
        expires_at = await tier_handler.get_tier_expiration(user.id)
        
        # Remove Premium tier (downgrade to free)
        await tier_handler.downgrade_user_tier(user.id, reason)
        
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
        
        if expires_at:
            embed.description += f"**Was set to expire:** {expires_at.strftime('%Y-%m-%d %H:%M UTC')}\n"
        
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
        await interaction.response.send_message(f"❌ Error removing Premium tier: {str(e)}", ephemeral=True)

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

@tree.command(name="removepro", description="[ADMIN] Remove Pro tier access from any Discord user", guild=discord.Object(id=YOUR_SERVER_ID))
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
        current_tier = await tier_handler.get_user_tier_async(user.id)
        if current_tier != 'pro':
            await interaction.response.send_message(
                f"❌ User {user.display_name} doesn't have Pro tier! Current tier: {current_tier.title()}",
                ephemeral=True
            )
            return
        
        # Get expiration info before removal
        expires_at = await tier_handler.get_tier_expiration(user.id)
        
        # Remove Pro tier (downgrade to free)
        await tier_handler.downgrade_user_tier(user.id, reason)
        
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
        
        if expires_at:
            embed.description += f"**Was set to expire:** {expires_at.strftime('%Y-%m-%d %H:%M UTC')}\n"
        
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
        await interaction.response.send_message(f"❌ Error removing Pro tier: {str(e)}", ephemeral=True)
        
@tree.command(name="checktier", description="[ADMIN] Check any user's current tier and expiration", guild=discord.Object(id=YOUR_SERVER_ID))
@app_commands.default_permissions(administrator=True)
@app_commands.describe(user="Discord user to check tier for")
async def check_tier(interaction: discord.Interaction, user: discord.User):
    if interaction.user.id != YOUR_ADMIN_ID:
        await interaction.response.send_message("❌ Bot owner only!", ephemeral=True)
        return
    
    try:
        # Get user's current tier
        current_tier = await tier_handler.get_user_tier_async(user.id)
        limits = tier_handler.get_limits(user.id)
        expires_at = await tier_handler.get_tier_expiration(user.id)
        tier_info = tier_handler.get_tier_info(current_tier)
        
        # Create detailed embed
        embed = discord.Embed(
            title=f"📊 Tier Information: {user.display_name}",
            description=f"**User ID:** `{user.id}`",
            color=tier_info['color']
        )
        
        # Current tier info
        embed.add_field(
            name=f"{tier_info['emoji']} Current Tier",
            value=f"**{tier_info['name']}** ({tier_info['price']})",
            inline=True
        )
        
        # Expiration info
        if expires_at:
            from datetime import datetime
            days_remaining = (expires_at - datetime.now()).days
            if days_remaining > 0:
                expiry_text = f"{expires_at.strftime('%Y-%m-%d %H:%M UTC')}\n({days_remaining} days remaining)"
                expiry_color = "🟢" if days_remaining > 7 else "🟡" if days_remaining > 3 else "🔴"
            else:
                expiry_text = f"{expires_at.strftime('%Y-%m-%d %H:%M UTC')}\n🔴 **EXPIRED**"
                expiry_color = "🔴"
            
            embed.add_field(
                name=f"{expiry_color} Expiration",
                value=expiry_text,
                inline=True
            )
        else:
            embed.add_field(
                name="⏰ Expiration",
                value="Permanent / No expiration",
                inline=True
            )
        
        # Tier limits
        text_limit = "Unlimited" if limits['text_limit'] == float('inf') else f"{limits['text_limit']:,} chars"
        voice_limit = "Unlimited" if limits['voice_limit'] == float('inf') else f"{limits['voice_limit']//60} minutes"
        
        embed.add_field(
            name="📋 Current Limits",
            value=(
                f"**Text:** {text_limit}\n"
                f"**Voice:** {voice_limit}\n"
                f"**Daily Points:** {limits['daily_points_min']}-{limits['daily_points_max']}"
            ),
            inline=False
        )
        
        # Features
        features = limits.get('features', [])
        if features:
            feature_text = "\n".join([f"• {feature.replace('_', ' ').title()}" for feature in features])
            embed.add_field(
                name="🎯 Available Features",
                value=feature_text,
                inline=False
            )
        
        if user.avatar:
            embed.set_thumbnail(url=user.avatar.url)
        
        embed.set_footer(text=f"Checked by {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    except Exception as e:
        await interaction.response.send_message(f"❌ Error checking tier: {str(e)}", ephemeral=True)

### 📈 **Tier Statistics**

@tree.command(name="tierstats", description="[ADMIN] View tier distribution statistics", guild=discord.Object(id=YOUR_SERVER_ID))
@app_commands.default_permissions(administrator=True)
async def tier_stats(interaction: discord.Interaction):
    if interaction.user.id != YOUR_ADMIN_ID:
        await interaction.response.send_message("❌ Bot owner only!", ephemeral=True)
        return
    
    try:
        # Get tier statistics
        stats = tier_handler.get_tier_stats()
        
        # Create statistics embed
        embed = discord.Embed(
            title="📈 Tier Distribution Statistics",
            description="Current tier membership breakdown",
            color=0x3498db
        )
        
        # Add tier counts
        embed.add_field(
            name=f"{TIER_EMOJIS['basic']} Basic Tier",
            value=f"**{stats['basic']}** users",
            inline=True
        )
        
        embed.add_field(
            name=f"{TIER_EMOJIS['premium']} Premium Tier",
            value=f"**{stats['premium']}** users",
            inline=True
        )
        
        embed.add_field(
            name=f"{TIER_EMOJIS['pro']} Pro Tier",
            value=f"**{stats['pro']}** users",
            inline=True
        )
        
        # Total premium users
        embed.add_field(
            name="💎 Total Premium Users",
            value=f"**{stats['total_premium']}** users",
            inline=False
        )
        
        # Revenue estimation (rough)
        estimated_revenue = (stats['basic'] * 1) + (stats['premium'] * 3) + (stats['pro'] * 5)
        embed.add_field(
            name="💰 Estimated Monthly Revenue",
            value=f"**${estimated_revenue}** USD",
            inline=True
        )
        
        embed.set_footer(text=f"Generated by {interaction.user.display_name}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    except Exception as e:
        await interaction.response.send_message(f"❌ Error getting tier stats: {str(e)}", ephemeral=True)

### 🧹 **Cleanup Expired Tiers**

@tree.command(name="cleanupexpired", description="[ADMIN] Clean up expired tier memberships", guild=discord.Object(id=YOUR_SERVER_ID))
@app_commands.default_permissions(administrator=True)
async def cleanup_expired(interaction: discord.Interaction):
    if interaction.user.id != YOUR_ADMIN_ID:
        await interaction.response.send_message("❌ Bot owner only!", ephemeral=True)
        return
    
    try:
        await interaction.response.defer(ephemeral=True)
        
        # Clean up expired tiers
        expired_users = await tier_handler.cleanup_expired_tiers()
        
        if not expired_users:
            embed = discord.Embed(
                title="✅ Cleanup Complete",
                description="No expired tier memberships found.",
                color=0x2ecc71
            )
        else:
            # Create summary of cleaned up users
            embed = discord.Embed(
                title="🧹 Cleanup Complete",
                description=f"Cleaned up **{len(expired_users)}** expired tier memberships:",
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
        
        embed.set_footer(text=f"Cleanup performed by {interaction.user.display_name}")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
    
    except Exception as e:
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
# NEW: Background task to clean up expired rewards
async def cleanup_expired_rewards():
    """Background task to clean up expired rewards"""
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
