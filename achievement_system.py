# -*- coding: utf-8 -*-
import sqlite3
import json
import logging
from datetime import datetime, date
from typing import Dict, List, Optional

logger = logging.getLogger('muse_achievements')

# Achievement definitions
ACHIEVEMENTS = {
    # Translation Achievements
    'first_translation': {
        'name': '🌟 First Steps',
        'description': 'Complete your first translation',
        'category': 'Translation',
        'rarity': 'Common',
        'points': 10,
        'requirement': 1,
        'stat': 'translations'
    },
    'translation_10': {
        'name': '📈 Getting Started',
        'description': 'Complete 10 translations',
        'category': 'Translation',
        'rarity': 'Common',
        'points': 25,
        'requirement': 10,
        'stat': 'translations'
    },
    'translation_50': {
        'name': '🎯 Dedicated Translator',
        'description': 'Complete 50 translations',
        'category': 'Translation',
        'rarity': 'Uncommon',
        'points': 75,
        'requirement': 50,
        'stat': 'translations'
    },
    'translation_100': {
        'name': '👑 Translation Master',
        'description': 'Complete 100 translations',
        'category': 'Translation',
        'rarity': 'Rare',
        'points': 150,
        'requirement': 100,
        'stat': 'translations'
    },
    'translation_500': {
        'name': '🏆 Translation Legend',
        'description': 'Complete 500 translations',
        'category': 'Translation',
        'rarity': 'Epic',
        'points': 300,
        'requirement': 500,
        'stat': 'translations'
    },
    
    # Language Achievements
    'languages_5': {
        'name': '🌍 Language Explorer',
        'description': 'Use 5 different languages',
        'category': 'Languages',
        'rarity': 'Common',
        'points': 30,
        'requirement': 5,
        'stat': 'unique_languages'
    },
    'languages_15': {
        'name': '🌎 Polyglot',
        'description': 'Use 15 different languages',
        'category': 'Languages',
        'rarity': 'Rare',
        'points': 100,
        'requirement': 15,
        'stat': 'unique_languages'
    },
    'languages_30': {
        'name': '🌏 Master Linguist',
        'description': 'Use 30 different languages',
        'category': 'Languages',
        'rarity': 'Epic',
        'points': 200,
        'requirement': 30,
        'stat': 'unique_languages'
    },
    
    # Voice Achievements
    'first_voice': {
        'name': '🎤 Voice Debut',
        'description': 'Use voice translation for the first time',
        'category': 'Voice',
        'rarity': 'Common',
        'points': 15,
        'requirement': 1,
        'stat': 'voice_sessions'
    },
    'voice_10': {
        'name': '🎙️ Voice Enthusiast',
        'description': 'Use voice translation 10 times',
        'category': 'Voice',
        'rarity': 'Uncommon',
        'points': 50,
        'requirement': 10,
        'stat': 'voice_sessions'
    },
    'voice_25': {
        'name': '📻 Voice Veteran',
        'description': 'Use voice translation 25 times',
        'category': 'Voice',
        'rarity': 'Rare',
        'points': 100,
        'requirement': 25,
        'stat': 'voice_sessions'
    },
    
    # Special Achievements
    'premium_supporter': {
        'name': '⭐ Premium Supporter',
        'description': 'Support Muse with premium',
        'category': 'Special',
        'rarity': 'Epic',
        'points': 200,
        'requirement': 'premium',
        'stat': 'premium'
    },
    'early_adopter': {
        'name': '🚀 Early Adopter',
        'description': 'One of the first 100 users',
        'category': 'Special',
        'rarity': 'Legendary',
        'points': 500,
        'requirement': 'early',
        'stat': 'early_user'
    }
}

# Rarity system
RARITY_INFO = {
    'Common': {'color': 0x95a5a6, 'emoji': '⚪'},
    'Uncommon': {'color': 0x2ecc71, 'emoji': '🟢'},
    'Rare': {'color': 0x3498db, 'emoji': '🔵'},
    'Epic': {'color': 0x9b59b6, 'emoji': '🟣'},
    'Legendary': {'color': 0xf1c40f, 'emoji': '🟡'}
}

class AchievementDatabase:
    def __init__(self, db_path: str = "muse_achievements.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize the achievement database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # User statistics table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_stats (
                        user_id INTEGER PRIMARY KEY,
                        total_translations INTEGER DEFAULT 0,
                        voice_sessions INTEGER DEFAULT 0,
                        languages_used TEXT DEFAULT '[]',
                        total_points INTEGER DEFAULT 0,
                        first_use_date TEXT,
                        last_active_date TEXT,
                        is_premium BOOLEAN DEFAULT FALSE,
                        is_early_user BOOLEAN DEFAULT FALSE,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # User achievements table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_achievements (
                        user_id INTEGER,
                        achievement_id TEXT,
                        earned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        points_earned INTEGER DEFAULT 0,
                        PRIMARY KEY (user_id, achievement_id)
                    )
                ''')
                
                conn.commit()
                logger.info("✅ Achievement database initialized")
                
        except Exception as e:
            logger.error(f"❌ Database initialization failed: {e}")
    
    def get_user_stats(self, user_id: int) -> Dict:
        """Get user statistics"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM user_stats WHERE user_id = ?", (user_id,))
                row = cursor.fetchone()
                
                if row:
                    return {
                        'user_id': row[0],
                        'total_translations': row[1],
                        'voice_sessions': row[2],
                        'languages_used': json.loads(row[3]) if row[3] else [],
                        'total_points': row[4],
                        'first_use_date': row[5],
                        'last_active_date': row[6],
                        'is_premium': bool(row[7]),
                        'is_early_user': bool(row[8]),
                        'unique_languages': len(json.loads(row[3])) if row[3] else 0
                    }
                else:
                    # Create new user
                    return self.create_user(user_id)
                    
        except Exception as e:
            logger.error(f"Error getting user stats: {e}")
            return {}
    
    def create_user(self, user_id: int) -> Dict:
        """Create a new user in the database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Check if this is an early user
                cursor.execute("SELECT COUNT(*) FROM user_stats")
                user_count = cursor.fetchone()[0]
                is_early = user_count < 100
                
                today = date.today().isoformat()
                
                cursor.execute('''
                    INSERT INTO user_stats 
                    (user_id, first_use_date, last_active_date, is_early_user) 
                    VALUES (?, ?, ?, ?)
                ''', (user_id, today, today, is_early))
                
                conn.commit()
                
                return {
                    'user_id': user_id,
                    'total_translations': 0,
                    'voice_sessions': 0,
                    'languages_used': [],
                    'total_points': 0,
                    'first_use_date': today,
                    'last_active_date': today,
                    'is_premium': False,
                    'is_early_user': is_early,
                    'unique_languages': 0
                }
                
        except Exception as e:
            logger.error(f"Error creating user: {e}")
            return {}
    
    def get_user_achievements(self, user_id: int) -> List[Dict]:
        """Get user's earned achievements"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT achievement_id, earned_at, points_earned 
                    FROM user_achievements 
                    WHERE user_id = ? 
                    ORDER BY earned_at DESC
                ''', (user_id,))
                
                achievements = []
                for row in cursor.fetchall():
                    ach_data = ACHIEVEMENTS.get(row[0], {})
                    achievements.append({
                        'id': row[0],
                        'name': ach_data.get('name', 'Unknown'),
                        'description': ach_data.get('description', ''),
                        'category': ach_data.get('category', 'Unknown'),
                        'rarity': ach_data.get('rarity', 'Common'),
                        'points': row[2],
                        'earned_at': row[1]
                    })
                
                return achievements
                
        except Exception as e:
            logger.error(f"Error getting achievements: {e}")
            return []
    
    def track_translation(self, user_id: int, source_lang: str = None, target_lang: str = None, is_premium: bool = False):
        """Track a translation and update stats"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get current stats
                stats = self.get_user_stats(user_id)
                languages_used = stats.get('languages_used', [])
                
                # Add new languages
                if source_lang and source_lang not in languages_used and source_lang != 'auto':
                    languages_used.append(source_lang)
                if target_lang and target_lang not in languages_used:
                    languages_used.append(target_lang)
                
                today = date.today().isoformat()
                
                # Update stats
                cursor.execute('''
                    UPDATE user_stats 
                    SET total_translations = total_translations + 1,
                        languages_used = ?,
                        last_active_date = ?,
                        is_premium = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (json.dumps(languages_used), today, is_premium, user_id))
                
                conn.commit()
                
                # Check for new achievements
                self.check_achievements(user_id)
                
        except Exception as e:
            logger.error(f"Error tracking translation: {e}")
    
    def track_voice_session(self, user_id: int, is_premium: bool = False):
        """Track a voice session"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                today = date.today().isoformat()
                
                cursor.execute('''
                    UPDATE user_stats 
                    SET voice_sessions = voice_sessions + 1,
                        last_active_date = ?,
                        is_premium = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (today, is_premium, user_id))
                
                conn.commit()
                
                # Check achievements
                self.check_achievements(user_id)
                
        except Exception as e:
            logger.error(f"Error tracking voice session: {e}")
    
    def check_achievements(self, user_id: int) -> List[str]:
        """Check and award new achievements"""
        try:
            stats = self.get_user_stats(user_id)
            current_achievements = [ach['id'] for ach in self.get_user_achievements(user_id)]
            new_achievements = []
            
            for ach_id, ach_data in ACHIEVEMENTS.items():
                if ach_id in current_achievements:
                    continue
                
                # Check if achievement is earned
                earned = False
                stat_type = ach_data['stat']
                requirement = ach_data['requirement']
                
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
                
                if earned:
                    self.award_achievement(user_id, ach_id, ach_data['points'])
                    new_achievements.append(ach_id)
            
            return new_achievements
            
        except Exception as e:
            logger.error(f"Error checking achievements: {e}")
            return []
    
    def award_achievement(self, user_id: int, achievement_id: str, points: int):
        """Award an achievement to a user"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Add achievement
                cursor.execute('''
                    INSERT OR IGNORE INTO user_achievements 
                    (user_id, achievement_id, points_earned) 
                    VALUES (?, ?, ?)
                ''', (user_id, achievement_id, points))
                
                # Update total points
                cursor.execute('''
                    UPDATE user_stats 
                    SET total_points = total_points + ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                ''', (points, user_id))
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"Error awarding achievement: {e}")

# Global achievement database instance
achievement_db = AchievementDatabase()

def get_rank_from_points(points: int) -> Dict:
    """Get user rank based on points"""
    if points >= 1000:
        return {'name': '🏆 Legend', 'color': 0xf1c40f}
    elif points >= 500:
        return {'name': '💎 Master', 'color': 0x9b59b6}
    elif points >= 250:
        return {'name': '🥇 Expert', 'color': 0xe67e22}
    elif points >= 100:
        return {'name': '🥈 Advanced', 'color': 0x3498db}
    elif points >= 50:
        return {'name': '🥉 Intermediate', 'color': 0x2ecc71}
    else:
        return {'name': '🌱 Beginner', 'color': 0x95a5a6}

async def send_achievement_notification(client, user_id: int, achievement_ids: List[str]):
    """Send achievement notification to user"""
    if not achievement_ids:
        return
    
    try:
        user = await client.fetch_user(user_id)
        if not user:
            return
        
        for ach_id in achievement_ids:
            ach_data = ACHIEVEMENTS.get(ach_id, {})
            rarity_info = RARITY_INFO.get(ach_data.get('rarity', 'Common'), {})
            
            embed = discord.Embed(
                title="🎉 Achievement Unlocked!",
                description=f"{rarity_info.get('emoji', '⚪')} **{ach_data.get('name', 'Unknown')}**\n{ach_data.get('description', '')}",
                color=rarity_info.get('color', 0x95a5a6)
            )
            
            embed.add_field(
                name="Points Earned",
                value=f"+{ach_data.get('points', 0)} points",
                inline=True
            )
            
            embed.add_field(
                name="Rarity",
                value=f"{rarity_info.get('emoji', '⚪')} {ach_data.get('rarity', 'Common')}",
                inline=True
            )
            
            embed.set_footer(text="Use /achievements to see all your achievements!")
            
            try:
                await user.send(embed=embed)
            except discord.Forbidden:
                # User has DMs disabled, skip notification
                pass
                
    except Exception as e:
        logger.error(f"Error sending achievement notification: {e}")

