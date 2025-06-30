# -*- coding: utf-8 -*-
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import discord

logger = logging.getLogger('muse_rewards')

ACHIEVEMENTS = {
    # Translation Achievements (Easy to track)
    'first_translation': {
        'name': '🌟 First Steps',
        'description': 'Complete your first translation',
        'category': 'Translation',
        'rarity': 'Common',
        'points': 10,
        'requirement': 1,
        'stat': 'translations'
    },
    'translation_5': {
        'name': '📝 Getting the Hang of It',
        'description': 'Complete 5 translations',
        'category': 'Translation',
        'rarity': 'Common',
        'points': 20,
        'requirement': 5,
        'stat': 'translations'
    },
    'translation_25': {
        'name': '🎯 Regular User',
        'description': 'Complete 25 translations',
        'category': 'Translation',
        'rarity': 'Uncommon',
        'points': 50,
        'requirement': 25,
        'stat': 'translations'
    },
    'translation_100': {
        'name': '👑 Translation Expert',
        'description': 'Complete 100 translations',
        'category': 'Translation',
        'rarity': 'Rare',
        'points': 150,
        'requirement': 100,
        'stat': 'translations'
    },
    'translation_250': {
        'name': '🏆 Translation Master',
        'description': 'Complete 250 translations',
        'category': 'Translation',
        'rarity': 'Epic',
        'points': 300,
        'requirement': 250,
        'stat': 'translations'
    },
    
    # Voice Achievements (Simple session tracking)
    'first_voice': {
        'name': '🎤 Voice Debut',
        'description': 'Use voice translation for the first time',
        'category': 'Voice',
        'rarity': 'Common',
        'points': 15,
        'requirement': 1,
        'stat': 'voice_sessions'
    },
    'voice_5': {
        'name': '🎙️ Voice User',
        'description': 'Use voice translation 5 times',
        'category': 'Voice',
        'rarity': 'Common',
        'points': 30,
        'requirement': 5,
        'stat': 'voice_sessions'
    },
    'voice_15': {
        'name': '📻 Voice Enthusiast',
        'description': 'Use voice translation 15 times',
        'category': 'Voice',
        'rarity': 'Uncommon',
        'points': 75,
        'requirement': 15,
        'stat': 'voice_sessions'
    },
    'voice_50': {
        'name': '🎵 Voice Master',
        'description': 'Use voice translation 50 times',
        'category': 'Voice',
        'rarity': 'Rare',
        'points': 200,
        'requirement': 50,
        'stat': 'voice_sessions'
    },
    
    # Command Usage Achievements (Track specific features)
    'auto_translate_user': {
        'name': '🔄 Auto Pilot',
        'description': 'Use auto-translation feature',
        'category': 'Features',
        'rarity': 'Common',
        'points': 25,
        'requirement': 1,
        'stat': 'auto_translate_used'
    },
    'dm_translator': {
        'name': '💌 Message Bridge',
        'description': 'Send 5 translated DMs',
        'category': 'Features',
        'rarity': 'Uncommon',
        'points': 40,
        'requirement': 5,
        'stat': 'dm_translations'
    },
    'context_menu_user': {
        'name': '📱 Right-Click Pro',
        'description': 'Use context menu translation 10 times',
        'category': 'Features',
        'rarity': 'Uncommon',
        'points': 35,
        'requirement': 10,
        'stat': 'context_menu_used'
    },
    
    # Tier-Based Achievements (Easy to track with your tier system)
    'basic_supporter': {
        'name': '💎 Basic Supporter',
        'description': 'Subscribe to Basic tier ($1/month)',
        'category': 'Support',
        'rarity': 'Uncommon',
        'points': 100,
        'requirement': 'basic',
        'stat': 'tier_basic'
    },
    'premium_supporter': {
        'name': '⭐ Premium Supporter',
        'description': 'Subscribe to Premium tier ($3/month)',
        'category': 'Support',
        'rarity': 'Rare',
        'points': 200,
        'requirement': 'premium',
        'stat': 'tier_premium'
    },
    'pro_supporter': {
        'name': '🚀 Pro Supporter',
        'description': 'Subscribe to Pro tier ($5/month)',
        'category': 'Support',
        'rarity': 'Epic',
        'points': 350,
        'requirement': 'pro',
        'stat': 'tier_pro'
    },
    'loyal_supporter': {
        'name': '💖 Loyal Supporter',
        'description': 'Maintain any paid tier for 30+ days',
        'category': 'Support',
        'rarity': 'Epic',
        'points': 250,
        'requirement': 30,
        'stat': 'days_subscribed'
    },
    
    # Point Purchase Achievements (Track Ko-fi donations)
    'first_donation': {
        'name': '🎁 First Donation',
        'description': 'Make your first point purchase',
        'category': 'Support',
        'rarity': 'Common',
        'points': 50,
        'requirement': 1,
        'stat': 'point_purchases'
    },
    'generous_donor': {
        'name': '💰 Generous Donor',
        'description': 'Purchase $20+ worth of points',
        'category': 'Support',
        'rarity': 'Rare',
        'points': 150,
        'requirement': 20,
        'stat': 'total_donated'
    },
    
    # Language Diversity (Simplified tracking)
    'language_explorer': {
        'name': '🌍 Language Explorer',
        'description': 'Translate to/from 3 different languages',
        'category': 'Languages',
        'rarity': 'Common',
        'points': 30,
        'requirement': 3,
        'stat': 'unique_languages'
    },
    'polyglot': {
        'name': '🌎 Polyglot',
        'description': 'Translate to/from 10 different languages',
        'category': 'Languages',
        'rarity': 'Uncommon',
        'points': 80,
        'requirement': 10,
        'stat': 'unique_languages'
    },
    'master_linguist': {
        'name': '🌏 Master Linguist',
        'description': 'Translate to/from 20 different languages',
        'category': 'Languages',
        'rarity': 'Rare',
        'points': 180,
        'requirement': 20,
        'stat': 'unique_languages'
    },
    
    # Time-Based Achievements (Simple date tracking)
    'daily_user': {
        'name': '📅 Daily User',
        'description': 'Use Muse for 7 different days',
        'category': 'Consistency',
        'rarity': 'Common',
        'points': 40,
        'requirement': 7,
        'stat': 'active_days'
    },
    'weekly_warrior': {
        'name': '🗓️ Weekly Warrior',
        'description': 'Use Muse for 30 different days',
        'category': 'Consistency',
        'rarity': 'Uncommon',
        'points': 100,
        'requirement': 30,
        'stat': 'active_days'
    },
    
    # Special/Fun Achievements
    'feedback_giver': {
        'name': '💬 Feedback Hero',
        'description': 'Provide feedback to help improve Muse',
        'category': 'Community',
        'rarity': 'Uncommon',
        'points': 60,
        'requirement': 1,
        'stat': 'feedback_given'
    },
    'server_inviter': {
        'name': '📢 Muse Ambassador',
        'description': 'Invite Muse to a new server',
        'category': 'Community',
        'rarity': 'Rare',
        'points': 120,
        'requirement': 1,
        'stat': 'servers_invited'
    },
    
    # Milestone Achievements
    'power_user': {
        'name': '⚡ Power User',
        'description': 'Reach 1000 total achievement points',
        'category': 'Milestones',
        'rarity': 'Epic',
        'points': 500,
        'requirement': 1000,
        'stat': 'total_achievement_points'
    },
    'muse_legend': {
        'name': '👑 Muse Legend',
        'description': 'Unlock 15 different achievements',
        'category': 'Milestones',
        'rarity': 'Legendary',
        'points': 750,
        'requirement': 15,
        'stat': 'achievements_unlocked'
    }
}
# Update the REWARDS dictionary - replace bulk_translation with enhanced_voice
REWARDS = {
    # === TIER UPGRADES ===
    'temp_basic_1d': {
        'name': '🥉 1-Day Basic Access',
        'description': 'Unlock Basic tier features for 24 hours (500 chars, 30min voice, history)',
        'cost': 50,
        'duration_hours': 24,
        'type': 'basic'
    },
    'temp_basic_3d': {
        'name': '🥉 3-Day Basic Access',
        'description': 'Unlock Basic tier features for 3 days',
        'cost': 120,
        'duration_hours': 72,
        'type': 'basic'
    },
    'temp_premium_1d': {
        'name': '🥈 1-Day Premium Access',
        'description': 'Unlock Premium tier features for 24 hours (2000 chars, 2h voice, priority)',
        'cost': 150,
        'duration_hours': 24,
        'type': 'premium'
    },
    'temp_premium_3d': {
        'name': '🥈 3-Day Premium Access',
        'description': 'Unlock Premium tier features for 3 days',
        'cost': 400,
        'duration_hours': 72,
        'type': 'premium'
    },
    'temp_premium_7d': {
        'name': '🥈 7-Day Premium Access',
        'description': 'Unlock Premium tier features for 1 week',
        'cost': 800,
        'duration_hours': 168,
        'type': 'premium'
    },
    'temp_pro_1d': {
        'name': '🥇 1-Day Pro Access',
        'description': 'Unlock Pro tier features for 24 hours (unlimited everything + beta access)',
        'cost': 250,
        'duration_hours': 24,
        'type': 'pro'
    },
    'temp_pro_3d': {
        'name': '🥇 3-Day Pro Access',
        'description': 'Unlock Pro tier features for 3 days',
        'cost': 650,
        'duration_hours': 72,
        'type': 'pro'
    },
    
    # === INDIVIDUAL FEATURES ===
    'translation_history': {
        'name': '📚 Translation History',
        'description': 'Access your translation history for 48 hours',
        'cost': 40,
        'duration_hours': 48,
        'type': 'feature'
    },
    'extended_limits': {
        'name': '📈 Extended Character Limit',
        'description': 'Increase your character limit to 1000 for 24 hours',
        'cost': 60,
        'duration_hours': 24,
        'type': 'feature'
    },
    'extended_voice': {
        'name': '🎤 Extended Voice Time',
        'description': 'Get 1 hour of additional voice translation time',
        'cost': 80,
        'duration_hours': 24,
        'type': 'feature'
    },
    'priority_processing': {
        'name': '⚡ Priority Processing',
        'description': 'Faster translation processing for 12 hours',
        'cost': 35,
        'duration_hours': 12,
        'type': 'feature'
    },
    'auto_translate_access': {
        'name': '🔄 Auto-Translate Feature',
        'description': 'Access auto-translate feature for 24 hours',
        'cost': 45,
        'duration_hours': 24,
        'type': 'feature'
    },
    
    # === BETA & SPECIAL FEATURES ===
    'enhanced_voice_beta': {
        'name': '🚀 Enhanced Voice Chat V2 (Beta)',
        'description': 'Access to advanced bidirectional voice translation for 48 hours',
        'cost': 100,
        'duration_hours': 48,
        'type': 'beta_feature'
    },
    'enhanced_voice_1d': {
        'name': '🚀 Enhanced Voice V2 (1 Day)',
        'description': 'Unlock advanced bidirectional voice translation for 24 hours',
        'cost': 50,
        'duration_hours': 24,
        'type': 'beta_feature'
    },
    'enhanced_voice_7d': {
        'name': '🚀 Enhanced Voice V2 (7 Days)', 
        'description': 'Unlock advanced bidirectional voice translation for 1 week',
        'cost': 300,
        'duration_hours': 168,  # 7 days * 24 hours
        'type': 'beta_feature'
    },

    
    # === COSMETIC & SOCIAL ===
    'custom_badge': {
        'name': '🎨 Custom Badge',
        'description': 'Create a custom badge for your profile (permanent)',
        'cost': 200,
        'duration_hours': -1,  # Permanent
        'type': 'cosmetic'
    },
    'profile_highlight': {
        'name': '✨ Profile Highlight',
        'description': 'Highlight your profile in leaderboards for 7 days',
        'cost': 90,
        'duration_hours': 168,
        'type': 'cosmetic'
    },
    
    # === POINT MULTIPLIERS ===
    'point_multiplier_2x': {
        'name': '💰 2x Point Multiplier',
        'description': 'Earn double points from all activities for 24 hours',
        'cost': 75,
        'duration_hours': 24,
        'type': 'multiplier'
    },
    'point_multiplier_3x': {
        'name': '💎 3x Point Multiplier',
        'description': 'Earn triple points from all activities for 12 hours',
        'cost': 150,
        'duration_hours': 12,
        'type': 'multiplier'
    },
    
    # === SPECIAL BUNDLES ===
    'starter_bundle': {
        'name': '🎁 Starter Bundle',
        'description': 'Basic access + History + Extended limits for 24h',
        'cost': 100,  # Discounted from 150
        'duration_hours': 24,
        'type': 'bundle',
        'includes': ['temp_basic_1d', 'translation_history', 'extended_limits']
    },
    'premium_bundle': {
        'name': '🎉 Premium Bundle',
        'description': 'Premium access + Beta features + 2x multiplier for 24h',
        'cost': 300,  # Discounted from 425
        'duration_hours': 24,
        'type': 'bundle',
        'includes': ['temp_premium_1d', 'beta_features', 'point_multiplier_2x']
    },
    'ultimate_bundle': {
        'name': '👑 Ultimate Bundle',
        'description': 'Pro access + All features + Custom badge for 3 days',
        'cost': 750,  # Discounted from 1000+
        'duration_hours': 72,
        'type': 'bundle',
        'includes': ['temp_pro_3d', 'beta_features', 'custom_badge', 'point_multiplier_2x']
    }
}

# Enhanced auto-badges with new tier system
AUTO_BADGES = {
    # === TRANSLATION MILESTONES ===
    'first_translation': {'emoji': '🌟', 'title': 'First Steps', 'description': 'Made your first translation'},
    'translation_10': {'emoji': '📈', 'title': 'Getting Started', 'description': 'Completed 10 translations'},
    'translation_25': {'emoji': '🎯', 'title': 'Regular User', 'description': 'Completed 25 translations'},
    'translation_50': {'emoji': '🏅', 'title': 'Dedicated', 'description': 'Completed 50 translations'},
    'translation_100': {'emoji': '👑', 'title': 'Master', 'description': 'Completed 100 translations'},
    'translation_250': {'emoji': '🏆', 'title': 'Expert', 'description': 'Completed 250 translations'},
    'translation_500': {'emoji': '💎', 'title': 'Legend', 'description': 'Completed 500 translations'},
    'translation_1000': {'emoji': '🌟', 'title': 'Grandmaster', 'description': 'Completed 1000 translations'},
    
    # === LANGUAGE DIVERSITY ===
    'languages_3': {'emoji': '🌍', 'title': 'Explorer', 'description': 'Used 3 different languages'},
    'languages_5': {'emoji': '🌎', 'title': 'Traveler', 'description': 'Used 5 different languages'},
    'languages_10': {'emoji': '🌏', 'title': 'Polyglot', 'description': 'Used 10 different languages'},
    'languages_15': {'emoji': '🗺️', 'title': 'Linguist', 'description': 'Used 15 different languages'},
    'languages_25': {'emoji': '🌐', 'title': 'Global Citizen', 'description': 'Used 25 different languages'},
    'languages_50': {'emoji': '🎓', 'title': 'Language Master', 'description': 'Used 50 different languages'},
    
    # === VOICE FEATURES ===
    'first_voice': {'emoji': '🎤', 'title': 'Voice User', 'description': 'Used voice translation'},
    'voice_10': {'emoji': '📻', 'title': 'Voice Regular', 'description': 'Used voice translation 10 times'},
    'voice_25': {'emoji': '🎙️', 'title': 'Voice Veteran', 'description': 'Used voice translation 25 times'},
    'voice_hours_1': {'emoji': '⏰', 'title': 'Chatterbox', 'description': 'Used 1 hour of voice translation'},
    'voice_hours_5': {'emoji': '🕐', 'title': 'Voice Enthusiast', 'description': 'Used 5 hours of voice translation'},
    
    # === TIER & SUBSCRIPTION ===
    'basic_subscriber': {'emoji': '🥉', 'title': 'Basic Supporter', 'description': 'Subscribed to Basic tier'},
    'premium_subscriber': {'emoji': '🥈', 'title': 'Premium Supporter', 'description': 'Subscribed to Premium tier'},
    'pro_subscriber': {'emoji': '🥇', 'title': 'Pro Supporter', 'description': 'Subscribed to Pro tier'},
    'loyal_subscriber': {'emoji': '💝', 'title': 'Loyal Supporter', 'description': 'Subscribed for 3+ months'},
    
    # === SPECIAL ACHIEVEMENTS ===
    'early_adopter': {'emoji': '🚀', 'title': 'Pioneer', 'description': 'Early adopter of Muse'},
    'beta_tester': {'emoji': '🧪', 'title': 'Beta Tester', 'description': 'Helped test beta features'},
    'community_helper': {'emoji': '🤝', 'title': 'Helper', 'description': 'Helped other users'},
    'feedback_provider': {'emoji': '💬', 'title': 'Contributor', 'description': 'Provided valuable feedback'},
    
    # === USAGE PATTERNS ===
    'daily_user': {'emoji': '📅', 'title': 'Daily User', 'description': 'Used Muse for 7 consecutive days'},
    'weekly_warrior': {'emoji': '🗓️', 'title': 'Weekly Warrior', 'description': 'Used Muse for 30 consecutive days'},
    'power_user': {'emoji': '⚡', 'title': 'Power User', 'description': 'Heavy usage across all features'},
    'night_owl': {'emoji': '🦉', 'title': 'Night Owl', 'description': 'Frequently uses Muse late at night'},
    'early_bird': {'emoji': '🐦', 'title': 'Early Bird', 'description': 'Frequently uses Muse early morning'},
    
    # === SOCIAL & SHARING ===
    'inviter': {'emoji': '📨', 'title': 'Inviter', 'description': 'Invited friends to use Muse'},
    'social_butterfly': {'emoji': '🦋', 'title': 'Social Butterfly', 'description': 'Used DM translation features'},
    'server_booster': {'emoji': '🚀', 'title': 'Server Booster', 'description': 'Added Muse to multiple servers'},
    
    # === POINT ACHIEVEMENTS ===
    'points_100': {'emoji': '💰', 'title': 'Saver', 'description': 'Earned 100 points'},
    'points_500': {'emoji': '💎', 'title': 'Collector', 'description': 'Earned 500 points'},
    'points_1000': {'emoji': '👑', 'title': 'Rich', 'description': 'Earned 1000 points'},
    'points_5000': {'emoji': '🏦', 'title': 'Wealthy', 'description': 'Earned 5000 points'},
    'big_spender': {'emoji': '💸', 'title': 'Big Spender', 'description': 'Spent 500+ points in shop'},
    
    # === SPECIAL EVENTS ===
    'holiday_user': {'emoji': '🎄', 'title': 'Holiday Spirit', 'description': 'Used Muse during holidays'},
    'anniversary': {'emoji': '🎂', 'title': 'Anniversary', 'description': 'Been with Muse for 1 year'},
    'milestone_witness': {'emoji': '🎉', 'title': 'Witness', 'description': 'Present during major milestones'}
}

# Reward categories for shop organization
REWARD_CATEGORIES = {
    'tier_upgrades': {
        'name': '⭐ Tier Upgrades',
        'description': 'Temporary access to higher tiers',
        'rewards': ['temp_basic_1d', 'temp_basic_3d', 'temp_premium_1d', 'temp_premium_3d', 'temp_premium_7d', 'temp_pro_1d', 'temp_pro_3d']
    },
    'features': {
        'name': '🎯 Individual Features',
        'description': 'Unlock specific features temporarily',
        'rewards': ['translation_history', 'extended_limits', 'extended_voice', 'priority_processing', 'auto_translate_access']
    },
    'beta': {
        'name': '🧪 Beta & Experimental',
        'description': 'Access to cutting-edge features',
        'rewards': ['enhanced_voice_beta', 'beta_features']
    },
    'multipliers': {
        'name': '💰 Point Multipliers',
        'description': 'Earn points faster',
        'rewards': ['point_multiplier_2x', 'point_multiplier_3x']
    },
    'cosmetic': {
        'name': '🎨 Cosmetic & Social',
        'description': 'Customize your profile',
        'rewards': ['custom_badge', 'profile_highlight']
    },
    'bundles': {
        'name': '🎁 Value Bundles',
        'description': 'Discounted feature combinations',
        'rewards': ['starter_bundle', 'premium_bundle', 'ultimate_bundle']
    }
}

# Point earning rates by tier
POINT_RATES = {
    'free': {
        'translation': 1,      # 1 point per translation
        'voice_minute': 2,     # 2 points per minute of voice
        'daily_bonus': 5,      # 5 points daily bonus
        'achievement': 10      # 10 points per achievement
    },
    'basic': {
        'translation': 2,      # 2x points for Basic users
        'voice_minute': 4,     # 2x points for voice
        'daily_bonus': 10,     # 2x daily bonus
        'achievement': 15      # 1.5x achievement bonus
    },
    'premium': {
        'translation': 3,      # 3x points for Premium users
        'voice_minute': 6,     # 3x points for voice
        'daily_bonus': 15,     # 3x daily bonus
        'achievement': 20      # 2x achievement bonus
    },
    'pro': {
        'translation': 5,      # 5x points for Pro users
        'voice_minute': 10,    # 5x points for voice
        'daily_bonus': 25,     # 5x daily bonus
        'achievement': 30      # 3x achievement bonus
    }
}

# Daily reward tiers
DAILY_REWARDS = {
    'free': {
        'base_points': 5,
        'bonus_chance': 0.1,   # 10% chance for bonus
        'bonus_points': 15,
        'streak_multiplier': 1.0
    },
    'basic': {
        'base_points': 10,     # 2x base points
        'bonus_chance': 0.15,  # 15% chance for bonus
        'bonus_points': 25,
        'streak_multiplier': 1.2
    },
    'premium': {
        'base_points': 15,     # 3x base points
        'bonus_chance': 0.2,   # 20% chance for bonus
        'bonus_points': 40,
        'streak_multiplier': 1.5
    },
    'pro': {
        'base_points': 25,     # 5x base points
        'bonus_chance': 0.3,   # 30% chance for bonus
        'bonus_points': 75,
        'streak_multiplier': 2.0
    }
}

# Achievement point rewards
ACHIEVEMENT_POINTS = {
    # Translation milestones
    'first_translation': 10,
    'translation_10': 25,
    'translation_25': 50,
    'translation_50': 100,
    'translation_100': 200,
    'translation_250': 500,
    'translation_500': 1000,
    'translation_1000': 2500,
    
    # Language diversity
    'languages_3': 30,
    'languages_5': 50,
    'languages_10': 100,
    'languages_15': 200,
    'languages_25': 500,
    'languages_50': 1500,
    
    # Voice achievements
    'first_voice': 20,
    'voice_10': 75,
    'voice_25': 150,
    'voice_hours_1': 100,
    'voice_hours_5': 300,
    
    # Tier achievements
    'basic_subscriber': 100,
    'premium_subscriber': 250,
    'pro_subscriber': 500,
    'loyal_subscriber': 1000,
    
    # Special achievements
    'early_adopter': 500,
    'beta_tester': 200,
    'community_helper': 150,
    'feedback_provider': 100,
    
    # Usage patterns
    'daily_user': 75,
    'weekly_warrior': 200,
    'power_user': 300,
    'night_owl': 50,
    'early_bird': 50,
    
    # Social achievements
    'inviter': 100,
    'social_butterfly': 75,
    'server_booster': 200,
    
    # Point milestones
    'points_100': 25,
    'points_500': 100,
    'points_1000': 250,
    'points_5000': 750,
    'big_spender': 200,
    
    # Special events
    'holiday_user': 100,
    'anniversary': 500,
    'milestone_witness': 300
}

# Feature access mapping for rewards
REWARD_FEATURE_ACCESS = {
    'temp_basic_1d': ['history', 'auto_translate'],
    'temp_basic_3d': ['history', 'auto_translate'],
    'temp_premium_1d': ['history', 'auto_translate', 'priority_processing', 'enhanced_voice'],
    'temp_premium_3d': ['history', 'auto_translate', 'priority_processing', 'enhanced_voice'],
    'temp_premium_7d': ['history', 'auto_translate', 'priority_processing', 'enhanced_voice'],
    'temp_pro_1d': ['all_features', 'beta_access', 'priority_support'],
    'temp_pro_3d': ['all_features', 'beta_access', 'priority_support'],
    'translation_history': ['history'],
    'auto_translate_access': ['auto_translate'],
    'enhanced_voice_beta': ['enhanced_voice'],
    'beta_features': ['beta_access'],
    'priority_processing': ['priority_processing']
}

# Bundle contents mapping
BUNDLE_CONTENTS = {
    'starter_bundle': {
        'rewards': ['temp_basic_1d', 'translation_history', 'extended_limits'],
        'total_value': 150,
        'discount': 50,
        'savings': '33%'
    },
    'premium_bundle': {
        'rewards': ['temp_premium_1d', 'beta_features', 'point_multiplier_2x'],
        'total_value': 425,
        'discount': 125,
        'savings': '29%'
    },
    'ultimate_bundle': {
        'rewards': ['temp_pro_3d', 'beta_features', 'custom_badge', 'point_multiplier_2x'],
        'total_value': 1025,
        'discount': 275,
        'savings': '27%'
    }
}

# Tier comparison for shop display
TIER_COMPARISON = {
    'free': {
        'name': '🆓 Free',
        'text_limit': '50 chars',
        'voice_limit': '5 min total',
        'features': ['Basic translation'],
        'points_multiplier': '1x',
        'daily_reward': '5 points'
    },
    'basic': {
        'name': '🥉 Basic ($1/month)',
        'text_limit': '500 chars',
        'voice_limit': '30 min total',
        'features': ['Translation history', 'Auto-translate', 'Basic translation'],
        'points_multiplier': '2x',
        'daily_reward': '10 points'
    },
    'premium': {
        'name': '🥈 Premium ($3/month)',
        'text_limit': '2000 chars',
        'voice_limit': '2 hours total',
        'features': ['Priority processing', 'Enhanced voice', 'All Basic features'],
        'points_multiplier': '3x',
        'daily_reward': '15 points'
    },
    'pro': {
        'name': '🥇 Pro ($5/month)',
        'text_limit': 'Unlimited',
        'voice_limit': 'Unlimited',
        'features': ['Beta access', 'Priority support', 'All features'],
        'points_multiplier': '5x',
        'daily_reward': '25 points'
    }
}

# Reward rarity system
REWARD_RARITY = {
    'common': {
        'color': 0x95a5a6,
        'emoji': '⚪',
        'rewards': ['extended_limits', 'priority_processing', 'translation_history']
    },
    'uncommon': {
        'color': 0x2ecc71,
        'emoji': '🟢',
        'rewards': ['temp_basic_1d', 'auto_translate_access', 'extended_voice']
    },
    'rare': {
        'color': 0x3498db,
        'emoji': '🔵',
        'rewards': ['temp_premium_1d', 'enhanced_voice_beta', 'point_multiplier_2x']
    },
    'epic': {
        'color': 0x9b59b6,
        'emoji': '🟣',
        'rewards': ['temp_premium_7d', 'temp_pro_1d', 'beta_features']
    },
    'legendary': {
        'color': 0xf39c12,
        'emoji': '🟡',
        'rewards': ['temp_pro_3d', 'ultimate_bundle', 'custom_badge']
    }
}

# Add this method to your RewardDatabase class
def get_user_rank(self, user_id: int) -> int:
    """Get user's rank position on leaderboard"""
    try:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get user's position by counting users with more points
            cursor.execute('''
                SELECT COUNT(*) + 1 as rank
                FROM users 
                WHERE points > (
                    SELECT points 
                    FROM users 
                    WHERE user_id = ?
                )
            ''', (user_id,))
            
            result = cursor.fetchone()
            return result[0] if result else None
            
    except Exception as e:
        logger.error(f"Error getting user rank: {e}")
        return None

# Helper function to get reward rarity
def get_reward_rarity(reward_id):
    """Get the rarity of a reward"""
    for rarity, data in REWARD_RARITY.items():
        if reward_id in data['rewards']:
            return rarity, data
    return 'common', REWARD_RARITY['common']

# Helper function to check if user has access to a feature
def user_has_feature_access(user_id, feature, reward_db, tier_handler):
    """Check if user has access to a specific feature"""
    # Check permanent tier access
    current_tier = tier_handler.get_user_tier(user_id)
    tier_features = tier_handler.tiers[current_tier].get('features', [])
    
    if feature in tier_features or 'all_features' in tier_features:
        return True
    
    # Check temporary access from rewards
    active_rewards = reward_db.get_active_rewards(user_id)
    for reward in active_rewards:
        reward_id = reward.get('reward_id', '')
        if reward_id in REWARD_FEATURE_ACCESS:
            reward_features = REWARD_FEATURE_ACCESS[reward_id]
            if feature in reward_features or 'all_features' in reward_features:
                return True
    
    return False

# Helper function to calculate points earned
def calculate_points_earned(user_id, action_type, amount, tier_handler):
    """Calculate points earned for an action"""
    current_tier = tier_handler.get_user_tier(user_id)
    rates = POINT_RATES.get(current_tier, POINT_RATES['free'])
    
    if action_type == 'translation':
        return rates['translation'] * amount
    elif action_type == 'voice_minute':
        return rates['voice_minute'] * amount
    elif action_type == 'daily_bonus':
        return rates['daily_bonus']
    elif action_type == 'achievement':
        return rates['achievement']
    
    return 0

# Helper function to get daily reward
def get_daily_reward(user_id, streak_days, tier_handler):
    """Calculate daily reward based on tier and streak"""
    current_tier = tier_handler.get_user_tier(user_id)
    reward_config = DAILY_REWARDS.get(current_tier, DAILY_REWARDS['free'])
    
    base_points = reward_config['base_points']
    
    # Apply streak multiplier
    streak_bonus = min(streak_days * 0.1, 1.0)  # Max 100% bonus at 10 day streak
    total_multiplier = reward_config['streak_multiplier'] + streak_bonus
    
    final_points = int(base_points * total_multiplier)
    
    # Check for bonus
    import random
    has_bonus = random.random() < reward_config['bonus_chance']
    if has_bonus:
        final_points += reward_config['bonus_points']
    
    return final_points, has_bonus



# Rank badges based on points
RANK_BADGES = {
    0: {'emoji': '🌱', 'title': 'Beginner', 'color': 0x95a5a6},
    50: {'emoji': '🥉', 'title': 'Intermediate', 'color': 0x2ecc71},
    100: {'emoji': '🥈', 'title': 'Advanced', 'color': 0x3498db},
    250: {'emoji': '🥇', 'title': 'Expert', 'color': 0xe67e22},
    500: {'emoji': '💎', 'title': 'Master', 'color': 0x9b59b6},
    1000: {'emoji': '🏆', 'title': 'Legend', 'color': 0xf1c40f}
}

class RewardDatabase:
    def __init__(self, db_path="rewards.db"):
        self.db_path = db_path
        self.db = None
        # Initialize sync database immediately
        self._init_sync_database()
    
    def _init_sync_database(self):
        """Initialize database with sync connection (for immediate setup)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Create user_stats table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_stats (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        total_points INTEGER DEFAULT 0,
                        total_earned INTEGER DEFAULT 0,
                        total_usage_hours REAL DEFAULT 0.0,
                        total_sessions INTEGER DEFAULT 0,
                        last_daily_claim DATE,
                        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create point_transactions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS point_transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        amount INTEGER,
                        transaction_type TEXT DEFAULT 'earned',
                        description TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES user_stats (user_id)
                    )
                """)
                
                # Create active_rewards table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS active_rewards (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        reward_id TEXT,
                        activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES user_stats (user_id)
                    )
                """)
                
                # Create user_achievements table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS user_achievements (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        achievement_id TEXT,
                        unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES user_stats (user_id),
                        UNIQUE(user_id, achievement_id)
                    )
                """)
                
                # Create reward_history table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS reward_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        reward_id TEXT,
                        points_spent INTEGER,
                        purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES user_stats (user_id)
                    )
                """)
                
                # Create daily_gifts table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS daily_gifts (
                        user_id INTEGER,
                        date TEXT,
                        total_gifted INTEGER DEFAULT 0,
                        PRIMARY KEY (user_id, date),
                        FOREIGN KEY (user_id) REFERENCES user_stats (user_id)
                    )
                """)
                
                conn.commit()
                logger.info("✅ All database tables created successfully")
                
        except Exception as e:
            logger.error(f"❌ Error initializing sync database: {e}")
    def _init_sync_database(self):
        """Initialize database with sync connection"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
            
                # Add this new table for tracking cashed out achievements
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS cashed_out_achievements (
                        user_id INTEGER,
                        achievement_id TEXT,
                        cashed_out_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        points_converted INTEGER,
                        PRIMARY KEY (user_id, achievement_id)
                    )
                """)
            
            # Your existing tables...
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error initializing database: {e}")

    def get_uncashed_achievement_points(self, user_id: int) -> tuple:
        """Get achievement points that haven't been cashed out yet"""
        try:
            from achievement_system import achievement_db, ACHIEVEMENTS
        
            # Get all user achievements
            user_achievements = achievement_db.get_user_achievements(user_id)
        
            # Get already cashed out achievements
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT achievement_id FROM cashed_out_achievements WHERE user_id = ?
                """, (user_id,))
                cashed_out = {row[0] for row in cursor.fetchall()}
        
            # Calculate uncashed points
            uncashed_points = 0
            uncashed_achievements = []
        
            for ach in user_achievements:
                ach_id = str(ach.get('id', '')) if isinstance(ach, dict) else str(ach)
            
                if ach_id not in cashed_out and ach_id in ACHIEVEMENTS:
                    points = ACHIEVEMENTS[ach_id].get('points', 0)
                    uncashed_points += points
                    uncashed_achievements.append(ach_id)
        
            return uncashed_points, uncashed_achievements
        
        except Exception as e:
            logger.error(f"Error getting uncashed achievement points: {e}")
            return 0, []

    def cash_out_achievements(self, user_id: int) -> int:
        """Cash out all uncashed achievements and mark them as cashed out"""
        try:
            uncashed_points, uncashed_achievements = self.get_uncashed_achievement_points(user_id)
        
            if uncashed_points > 0:
                # Add points to user's balance
                self.add_points(user_id, uncashed_points, "Achievement cashout")
            
                # Mark achievements as cashed out
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                
                    for ach_id in uncashed_achievements:
                        points = ACHIEVEMENTS.get(ach_id, {}).get('points', 0)
                        cursor.execute("""
                            INSERT OR REPLACE INTO cashed_out_achievements 
                            (user_id, achievement_id, points_converted)
                            VALUES (?, ?, ?)
                        """, (user_id, ach_id, points))
                
                    conn.commit()
            
                logger.info(f"Cashed out {uncashed_points} points from {len(uncashed_achievements)} achievements for user {user_id}")
        
            return uncashed_points
        
        except Exception as e:
            logger.error(f"Error cashing out achievements: {e}")
            return 0

    def get_total_points_including_achievements(self, user_id: int) -> int:
        """Get total points including uncashed achievement points"""
        try:
            # Get regular activity points
            user_data = self.get_or_create_user(user_id, "")
            activity_points = user_data.get('points', 0)
        
            # Get uncashed achievement points
            uncashed_points, _ = self.get_uncashed_achievement_points(user_id)
        
            return activity_points + uncashed_points
        
        except Exception as e:
            logger.error(f"Error getting total points: {e}")
            return 0

    async def connect(self):
        """Connect to async database"""
        import aiosqlite
        self.db = await aiosqlite.connect(self.db_path)
        # Tables are already created by sync init
        logger.info("✅ Async database connection established")
    
    async def initialize_database(self):
        """Initialize database (alias for init_tables for compatibility)"""
        await self.init_tables()
        logger.info("✅ Database initialized via initialize_database method")


    async def init_tables(self):
        """Initialize database tables (async version - kept for compatibility)"""
        # Tables are already created in __init__, but we can double-check here
        try:
            # Just verify the tables exist
            await self.db.execute("SELECT name FROM sqlite_master WHERE type='table'")
            logger.info("✅ Database tables verified")
        except Exception as e:
            logger.error(f"❌ Error verifying tables: {e}")
    
    # Keep all your existing methods exactly as they are...
    # Just add this debug method:
    
    def debug_tables(self):
        """Debug method to check what tables exist"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                
                print("🔍 DEBUG: Available tables:")
                for table in tables:
                    print(f"  - {table[0]}")
                    
                return [table[0] for table in tables]
                
        except Exception as e:
            logger.error(f"Debug tables error: {e}")
            return []
    async def ensure_user_exists(self, user_id: int, username: str = "Unknown"):
        """Ensure user exists in database"""
        await self.db.execute(
            "INSERT OR IGNORE INTO users (user_id, username) VALUES (?, ?)",
            (user_id, username)
        )
        await self.db.commit()
    
    async def add_points(self, user_id: int, points: int, reason: str = ""):
        """Add points to user"""
        await self.ensure_user_exists(user_id)
        
        await self.db.execute(
            "UPDATE users SET points = points + ? WHERE user_id = ?",
            (points, user_id)
        )
        
        await self.db.execute(
            "INSERT INTO point_transactions (user_id, points, reason) VALUES (?, ?, ?)",
            (user_id, points, reason)
        )
        
        await self.db.commit()
        return True
    
    async def increment_stat(self, user_id: int, stat_name: str, amount: int = 1):
        """Increment user statistic"""
        await self.ensure_user_exists(user_id)
        
        await self.db.execute(
            f"UPDATE users SET {stat_name} = COALESCE({stat_name}, 0) + ? WHERE user_id = ?",
            (amount, user_id)
        )
        await self.db.commit()
        return True
    
    async def get_user(self, user_id: int):
        """Get user data"""
        cursor = await self.db.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,)
        )
        result = await cursor.fetchone()
        
        if result:
            return dict(result)
        return None

    
    def get_or_create_user(self, user_id: int, username: str) -> Dict:
        """Get user data or create new user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Try to get existing user
                cursor.execute('''
                    SELECT user_id, username, total_points, total_earned, 
                           total_usage_hours, total_sessions, last_daily_claim,
                           last_activity, created_at, updated_at
                    FROM user_stats WHERE user_id = ?
                ''', (user_id,))
                
                row = cursor.fetchone()
                
                if row:
                    # Update username if changed
                    if row[1] != username:
                        cursor.execute('''
                            UPDATE user_stats SET username = ?, updated_at = CURRENT_TIMESTAMP
                            WHERE user_id = ?
                        ''', (username, user_id))
                        conn.commit()
                    
                    return {
                        'user_id': row[0],
                        'username': username,  # Use updated username
                        'points': row[2],
                        'total_earned': row[3],
                        'total_usage_hours': row[4],
                        'total_sessions': row[5],
                        'last_daily_claim': row[6],
                        'last_activity': row[7],
                        'created_at': row[8],
                        'updated_at': row[9]
                    }
                else:
                    # Create new user
                    cursor.execute('''
                        INSERT INTO user_stats (user_id, username)
                        VALUES (?, ?)
                    ''', (user_id, username))
                    conn.commit()
                    
                    return {
                        'user_id': user_id,
                        'username': username,
                        'points': 0,
                        'total_earned': 0,
                        'total_usage_hours': 0.0,
                        'total_sessions': 0,
                        'last_daily_claim': None,
                        'last_activity': datetime.now().isoformat(),
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat()
                    }
                    
        except Exception as e:
            logger.error(f"Error getting/creating user {user_id}: {e}")
            return {
                'user_id': user_id,
                'username': username,
                'points': 0,
                'total_earned': 0,
                'total_usage_hours': 0.0,
                'total_sessions': 0,
                'last_daily_claim': None,
                'last_activity': datetime.now().isoformat(),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
    
    def add_points(self, user_id: int, amount: int, description: str = "Points earned") -> bool:
        """Add points to user account"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Update user points
                cursor.execute('''
                    UPDATE user_stats 
                    SET total_points = total_points + ?,
                        total_earned = total_earned + ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (amount, max(0, amount), user_id))  # Only count positive amounts as earned
                
                # Record transaction
                cursor.execute('''
                    INSERT INTO point_transactions (user_id, amount, transaction_type, description)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, amount, "earned" if amount > 0 else "spent", description))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error adding points to user {user_id}: {e}")
            return False
    
    def purchase_reward(self, user_id: int, reward_id: str) -> Dict:
        """Purchase a reward with points"""
        try:
            reward = REWARDS.get(reward_id)
            if not reward:
                return {'success': False, 'error': 'Invalid reward ID'}
            
            user_data = self.get_or_create_user(user_id, f"User_{user_id}")
            
            # Check if user has enough points
            if user_data['points'] < reward['cost']:
                return {
                    'success': False,
                    'error': f"Not enough points! Need {reward['cost']}, have {user_data['points']}"
                }
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Calculate expiration time
                expires_at = datetime.now() + timedelta(hours=reward['duration_hours'])
                
                # Add active reward
                cursor.execute('''
                    INSERT OR REPLACE INTO active_rewards
                    (user_id, reward_id, expires_at)
                    VALUES (?, ?, ?)
                ''', (user_id, reward_id, expires_at.isoformat()))
                
                # Add to purchase history
                cursor.execute('''
                    INSERT INTO reward_history
                    (user_id, reward_id, points_spent)
                    VALUES (?, ?, ?)
                ''', (user_id, reward_id, reward['cost']))
                
                # Deduct points from user
                cursor.execute('''
                    UPDATE user_stats
                    SET total_points = total_points - ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (reward['cost'], user_id))
                
                # Record transaction
                cursor.execute('''
                    INSERT INTO point_transactions (user_id, amount, transaction_type, description)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, -reward['cost'], "spent", f"Purchased {reward['name']}"))
                
                conn.commit()
                
                return {
                    'success': True,
                    'reward': reward,
                    'expires_at': expires_at,
                    'points_remaining': user_data['points'] - reward['cost']
                }
                
        except Exception as e:
            logger.error(f"Error purchasing reward: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_active_rewards(self, user_id: int) -> List[Dict]:
        """Get user's active rewards"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Clean up expired rewards first
                cursor.execute('''
                    DELETE FROM active_rewards
                    WHERE expires_at < ?
                ''', (datetime.now().isoformat(),))
                
                # Get active rewards
                cursor.execute('''
                    SELECT reward_id, activated_at, expires_at
                    FROM active_rewards
                    WHERE user_id = ? AND expires_at > ?
                ''', (user_id, datetime.now().isoformat()))
                
                active_rewards = []
                for row in cursor.fetchall():
                    reward_data = REWARDS.get(row[0], {})
                    active_rewards.append({
                        'id': row[0],
                        'name': reward_data.get('name', 'Unknown'),
                        'type': reward_data.get('type', 'unknown'),
                        'activated_at': row[1],
                        'expires_at': row[2]
                    })
                
                conn.commit()
                return active_rewards
                
        except Exception as e:
            logger.error(f"Error getting active rewards: {e}")
            return []
    
    def has_active_reward(self, user_id: int, reward_type: str) -> bool:
        """Check if user has an active reward of specific type"""
        active_rewards = self.get_active_rewards(user_id)
        return any(reward['type'] == reward_type for reward in active_rewards)
    
    def claim_daily_reward(self, user_id: int, username: str, is_premium: bool = False) -> Dict:
        """Claim daily reward points"""
        try:
            user_data = self.get_or_create_user(user_id, username)
            today = datetime.now().date().isoformat()
            
            # Check if already claimed today
            if user_data['last_daily_claim'] == today:
                return {
                    'success': False,
                    'error': 'Daily reward already claimed today!',
                    'next_claim': 'tomorrow'
                }
            
            # Calculate reward amount
            base_reward = 25 if is_premium else 10
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Update user points and daily claim
                                # Update user points and daily claim
                cursor.execute('''
                    UPDATE user_stats 
                    SET total_points = total_points + ?,
                        total_earned = total_earned + ?,
                        last_daily_claim = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (base_reward, base_reward, today, user_id))
                
                # Record transaction
                cursor.execute('''
                    INSERT INTO point_transactions (user_id, amount, transaction_type, description)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, base_reward, "daily", f"Daily reward ({'Premium' if is_premium else 'Free'})"))
                
                conn.commit()
                
                return {
                    'success': True,
                    'points_earned': base_reward,
                    'total_points': user_data['points'] + base_reward,
                    'is_premium': is_premium
                }
                
        except Exception as e:
            logger.error(f"Error claiming daily reward for user {user_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Get top users by points"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT user_id, username, total_points, total_earned, total_usage_hours
                    FROM user_stats
                    ORDER BY total_points DESC
                    LIMIT ?
                ''', (limit,))
                
                leaderboard = []
                for row in cursor.fetchall():
                    leaderboard.append({
                        'user_id': row[0],
                        'username': row[1],
                        'points': row[2],
                        'total_earned': row[3],
                        'total_usage_hours': row[4]
                    })
                
                return leaderboard
                
        except Exception as e:
            logger.error(f"Error getting leaderboard: {e}")
            return []
    
    def get_user_rank(self, user_id: int) -> Optional[int]:
        """Get user's rank on leaderboard"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT COUNT(*) + 1 as rank
                    FROM user_stats u1, user_stats u2
                    WHERE u1.user_id = ? AND u2.total_points > u1.total_points
                ''', (user_id,))
                
                result = cursor.fetchone()
                return result[0] if result else None
                
        except Exception as e:
            logger.error(f"Error getting user rank: {e}")
            return None
    
    def transfer_points(self, from_user_id: int, to_user_id: int, amount: int, description: str) -> bool:
        """Transfer points between users"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if sender has enough points
                cursor.execute('SELECT total_points FROM user_stats WHERE user_id = ?', (from_user_id,))
                sender_points = cursor.fetchone()
                
                if not sender_points or sender_points[0] < amount:
                    return False
                
                # Perform transfer
                cursor.execute('''
                    UPDATE user_stats 
                    SET total_points = total_points - ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (amount, from_user_id))
                
                cursor.execute('''
                    UPDATE user_stats 
                    SET total_points = total_points + ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (amount, to_user_id))
                
                # Record transactions
                cursor.execute('''
                    INSERT INTO point_transactions (user_id, amount, transaction_type, description)
                    VALUES (?, ?, ?, ?)
                ''', (from_user_id, -amount, "transfer_out", description))
                
                cursor.execute('''
                    INSERT INTO point_transactions (user_id, amount, transaction_type, description)
                    VALUES (?, ?, ?, ?)
                ''', (to_user_id, amount, "transfer_in", description))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error transferring points: {e}")
            return False
    
    def get_daily_gifted(self, user_id: int, date) -> int:
        """Get total points gifted by user today"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                date_str = date.isoformat() if hasattr(date, 'isoformat') else str(date)
                
                cursor.execute('''
                    SELECT COALESCE(total_gifted, 0)
                    FROM daily_gifts
                    WHERE user_id = ? AND date = ?
                ''', (user_id, date_str))
                
                result = cursor.fetchone()
                return result[0] if result else 0
                
        except Exception as e:
            logger.error(f"Error getting daily gifted amount: {e}")
            return 0
    
    def record_daily_gift(self, user_id: int, amount: int, date) -> bool:
        """Record daily gift amount"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                date_str = date.isoformat() if hasattr(date, 'isoformat') else str(date)
                
                cursor.execute('''
                    INSERT OR REPLACE INTO daily_gifts (user_id, date, total_gifted)
                    VALUES (?, ?, COALESCE((SELECT total_gifted FROM daily_gifts WHERE user_id = ? AND date = ?), 0) + ?)
                ''', (user_id, date_str, user_id, date_str, amount))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error recording daily gift: {e}")
            return False
    
    def update_usage_time(self, user_id: int, hours: float) -> bool:
        """Update user's total usage time"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE user_stats 
                    SET total_usage_hours = total_usage_hours + ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (hours, user_id))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error updating usage time: {e}")
            return False
    def get_total_points_including_achievements(self, user_id: int) -> int:
        """Get total points including unconverted achievement points"""
        try:
            # Get regular activity points
            user_data = self.get_or_create_user(user_id, "")
            activity_points = user_data.get('points', 0)
        
            # Calculate achievement points
            try:
                from achievement_system import achievement_db, ACHIEVEMENTS
                user_achievements = achievement_db.get_user_achievements(user_id)
                achievement_points = 0
            
                for ach in user_achievements:
                    ach_id = str(ach.get('id', '')) if isinstance(ach, dict) else str(ach)
                    if ach_id in ACHIEVEMENTS:
                        achievement_points += ACHIEVEMENTS[ach_id].get('points', 0)
            except:
                achievement_points = 0
        
            return activity_points + achievement_points
        
        except Exception as e:
            logger.error(f"Error getting total points: {e}")
            return 0

    def increment_session_count(self, user_id: int) -> bool:
        """Increment user's session count"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    UPDATE user_stats 
                    SET total_sessions = total_sessions + 1,
                        last_activity = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (user_id,))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error incrementing session count: {e}")
            return False
    
    def get_user_achievements(self, user_id: int):
        """Get user's achievement IDs from achievement database"""
        try:
            # Import here to avoid circular imports
            from achievement_system import achievement_db
        
            user_achievements = achievement_db.get_user_achievements(user_id)
            # Extract just the IDs
            achievement_ids = []
            for ach in user_achievements:
                if isinstance(ach, dict):
                    achievement_ids.append(ach.get('id', ''))
                else:
                    achievement_ids.append(str(ach))
        
            return achievement_ids
        
        except Exception as e:
            logger.error(f"Error getting user achievements: {e}")
            return []
    
    
    def unlock_achievement(self, user_id: int, achievement_id: str) -> bool:
        """Unlock an achievement for user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    INSERT OR IGNORE INTO user_achievements (user_id, achievement_id)
                    VALUES (?, ?)
                ''', (user_id, achievement_id))
                
                conn.commit()
                return cursor.rowcount > 0  # Returns True if new achievement was added
                
        except Exception as e:
            logger.error(f"Error unlocking achievement: {e}")
            return False
    
    def get_user_badges(self, user_id: int, achievements: List[str], points: int) -> List[Dict]:
        """Get user's auto-badges based on achievements and points"""
        badges = []
        
        # Achievement badges
        for achievement_id in achievements:
            if achievement_id in AUTO_BADGES:
                badge_info = AUTO_BADGES[achievement_id]
                badges.append({
                    'emoji': badge_info['emoji'],
                    'title': badge_info['title'],
                    'type': 'achievement',
                    'source': achievement_id
                })
        
        # Rank badge (highest rank only)
        user_rank = None
        for min_points in sorted(RANK_BADGES.keys(), reverse=True):
            if points >= min_points:
                user_rank = RANK_BADGES[min_points]
                break
        
        if user_rank:
            badges.append({
                'emoji': user_rank['emoji'],
                'title': user_rank['title'],
                'type': 'rank',
                'color': user_rank['color']
            })
        
        return badges
    
    def get_total_users(self) -> int:
        """Get total number of users"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COUNT(*) FROM user_stats')
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error getting total users: {e}")
            return 0
    
    def get_total_points_distributed(self) -> int:
        """Get total points distributed across all users"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT COALESCE(SUM(total_earned), 0) FROM user_stats')
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error getting total points distributed: {e}")
            return 0
    
    def reset_daily_claim(self, user_id: int) -> bool:
        """Reset user's daily claim (admin function)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE user_stats 
                    SET last_daily_claim = NULL, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (user_id,))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error resetting daily claim: {e}")
            return False
    
    def cleanup_expired_rewards(self) -> int:
        """Clean up expired rewards and return count of cleaned items"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    DELETE FROM active_rewards
                    WHERE expires_at < ?
                ''', (datetime.now().isoformat(),))
                
                cleaned_count = cursor.rowcount
                conn.commit()
                
                if cleaned_count > 0:
                    logger.info(f"Cleaned up {cleaned_count} expired rewards")
                
                return cleaned_count
                
        except Exception as e:
            logger.error(f"Error cleaning up expired rewards: {e}")
            return 0
    
    def get_point_transactions(self, user_id: int, limit: int = 10) -> List[Dict]:
        """Get user's recent point transactions"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT amount, transaction_type, description, timestamp
                    FROM point_transactions
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (user_id, limit))
                
                transactions = []
                for row in cursor.fetchall():
                    transactions.append({
                        'amount': row[0],
                        'type': row[1],
                        'description': row[2],
                        'timestamp': row[3]
                    })
                
                return transactions
                
        except Exception as e:
            logger.error(f"Error getting point transactions: {e}")
            return []
    
    def close(self):
        """Close database connections (cleanup method)"""
        # SQLite connections are closed automatically with context managers
        # This method is here for compatibility and future extensions
        logger.info("Reward database cleanup completed")

# Utility functions for integration
def get_enhanced_user_limits(user_id: int, base_limits: Dict, is_premium: bool, reward_db_instance) -> Dict:
    """Get user limits enhanced by active rewards"""
    limits = base_limits.copy()
    
    # Check for active rewards
    active_rewards = reward_db_instance.get_active_rewards(user_id)
    
    for reward in active_rewards:
        if reward['type'] == 'premium':
            # Temporary premium overrides base limits
            limits['text_limit'] = float('inf')
            limits['voice_limit'] = float('inf')
        elif reward['type'] == 'feature' and reward['id'] == 'extended_limits':
            # Double the text limit
            if limits['text_limit'] != float('inf'):
                limits['text_limit'] *= 2
    
    return limits

async def handle_enhanced_voice_purchase(user_id: int, item_key: str, item_data: dict):
    """Handle purchase of enhanced voice beta access"""
    try:
        user_data = reward_db.get_or_create_user(user_id, "Unknown")
        cost = item_data['cost']
        
        # Check if user has enough points
        if user_data['points'] < cost:
            return False, f"Insufficient points! Need {cost:,}, have {user_data['points']:,}"
        
        from datetime import datetime, timedelta
        duration_hours = item_data['duration_hours']
        expires_at = datetime.now() + timedelta(hours=duration_hours)
        
        # Deduct points and grant access
        reward_db.add_points(user_id, -cost, f"Purchased {item_data['name']}")
        reward_db.set_user_data(user_id, 'enhanced_voice_access', expires_at.isoformat())
        
        return True, f"Enhanced Voice V2 access granted until {expires_at.strftime('%Y-%m-%d %H:%M')}"
        
    except Exception as e:
        logger.error(f"Error purchasing enhanced voice access: {e}")
        return False, "Purchase failed due to technical error"


def has_priority_processing(user_id: int, reward_db_instance) -> bool:
    """Check if user has priority processing active"""
    return reward_db_instance.has_active_reward(user_id, 'feature') and \
           any(r['id'] == 'priority_processing' for r in reward_db_instance.get_active_rewards(user_id))

def has_enhanced_voice_access(user_id: int, reward_db, tier_handler) -> bool:
    """
    Check if user has access to enhanced voice features (voicechat2)
    Access granted to: Premium, Pro tiers, or users with purchased enhanced voice access
    """
    try:
        # Get user's current tier
        current_tier = tier_handler.get_user_tier(user_id)
        
        # Premium and Pro users get unlimited access
        if current_tier in ['premium', 'pro']:
            return True
        
        # Check for purchased enhanced voice access
        user_data = reward_db.get_or_create_user(user_id, "Unknown")
        
        from datetime import datetime
        
        # Check enhanced voice access
        if 'enhanced_voice_access' in user_data:
            access_expires = datetime.fromisoformat(user_data['enhanced_voice_access'])
            if datetime.now() < access_expires:
                return True
        
        # No access for free and basic tiers without purchase
        return False
        
    except Exception as e:
        logger.error(f"Error checking enhanced voice access for user {user_id}: {e}")
        return False

# Add this method to your RewardDatabase class
def add_session(self, user_id: int, username: str = None):
    """Add a session count for the user"""
    try:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get or create user first
            user_data = self.get_or_create_user(user_id, username)
            
            # Increment session count
            cursor.execute('''
                UPDATE users 
                SET total_sessions = total_sessions + 1,
                    last_active = ?
                WHERE user_id = ?
            ''', (datetime.now().isoformat(), user_id))
            
            conn.commit()
            logger.info(f"Added session for user {user_id}")
            
    except Exception as e:
        logger.error(f"Error adding session for user {user_id}: {e}")

def award_achievement(self, user_id: int, achievement_id: str, points: int):
    """Award achievement - compatibility method"""
    try:
        # Just add points since we're using the reward system for achievements
        self.add_points(user_id, points, f"Achievement: {achievement_id}")
        logger.info(f"✅ Awarded achievement {achievement_id} ({points} points) to user {user_id}")
        return True
    except Exception as e:
        logger.error(f"Error awarding achievement: {e}")
        return False

# Add this method to your RewardDatabase class:

def increment_stat(self, user_id: int, stat_name: str, amount: int = 1) -> bool:
    """Increment a user statistic"""
    try:
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # For now, we'll just update session count since that's what we have
            if stat_name in ['text_translations', 'total_translations']:
                cursor.execute('''
                    UPDATE user_stats
                    SET total_sessions = total_sessions + ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (amount, user_id))
            
            conn.commit()
            return True
            
    except Exception as e:
        logger.error(f"Error incrementing stat {stat_name}: {e}")
        return False


# Global reward database instance (to be imported by main bot file)
reward_db = RewardDatabase(db_path="muse_bot.db")
