# -*- coding: utf-8 -*-
import sqlite3
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import discord

logger = logging.getLogger('muse_rewards')

# Update the REWARDS dictionary - replace bulk_translation with enhanced_voice
REWARDS = {
    'temp_premium_1d': {
        'name': '⭐ 1-Day Premium',
        'description': 'Unlock premium features for 24 hours',
        'cost': 100,
        'duration_hours': 24,
        'type': 'premium'
    },
    'temp_premium_7d': {
        'name': '💎 7-Day Premium',
        'description': 'Unlock premium features for 1 week',
        'cost': 600,
        'duration_hours': 168,
        'type': 'premium'
    },
    'extended_limits': {
        'name': '📈 Extended Limits',
        'description': 'Double your character limit for 24 hours',
        'cost': 50,
        'duration_hours': 24,
        'type': 'feature'
    },
    'priority_processing': {
        'name': '⚡ Priority Processing',
        'description': 'Faster translation processing for 12 hours',
        'cost': 30,
        'duration_hours': 12,
        'type': 'feature'
    },
    'enhanced_voice_beta': {
        'name': '🚀 Enhanced Voice Chat V2 (Beta)',
        'description': 'Access to advanced bidirectional voice translation for 48 hours',
        'cost': 75,
        'duration_hours': 48,
        'type': 'beta_feature'
    }
}

# Auto-badges based on achievements
AUTO_BADGES = {
    'first_translation': {'emoji': '🌟', 'title': 'First Steps'},
    'translation_10': {'emoji': '📈', 'title': 'Getting Started'},
    'translation_50': {'emoji': '🎯', 'title': 'Dedicated'},
    'translation_100': {'emoji': '👑', 'title': 'Master'},
    'translation_500': {'emoji': '🏆', 'title': 'Legend'},
    'languages_5': {'emoji': '🌍', 'title': 'Explorer'},
    'languages_15': {'emoji': '🌎', 'title': 'Polyglot'},
    'languages_30': {'emoji': '🌏', 'title': 'Linguist'},
    'first_voice': {'emoji': '🎤', 'title': 'Voice User'},
    'voice_25': {'emoji': '📻', 'title': 'Voice Veteran'},
    'premium_supporter': {'emoji': '⭐', 'title': 'Supporter'},
    'early_adopter': {'emoji': '🚀', 'title': 'Pioneer'}
}

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
    def __init__(self, db_path: str = "muse_rewards.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Initialize all database tables"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # User stats table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_stats (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,
                        total_points INTEGER DEFAULT 0,
                        total_earned INTEGER DEFAULT 0,
                        total_usage_hours REAL DEFAULT 0.0,
                        total_sessions INTEGER DEFAULT 0,
                        last_daily_claim TEXT,
                        last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Active rewards table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS active_rewards (
                        user_id INTEGER,
                        reward_id TEXT,
                        activated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        expires_at TIMESTAMP,
                        PRIMARY KEY (user_id, reward_id)
                    )
                ''')
                
                # Reward purchase history
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS reward_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        reward_id TEXT,
                        points_spent INTEGER,
                        purchased_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Point transactions table
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS point_transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        amount INTEGER,
                        transaction_type TEXT,
                        description TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Daily gift tracking
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS daily_gifts (
                        user_id INTEGER,
                        date TEXT,
                        total_gifted INTEGER DEFAULT 0,
                        PRIMARY KEY (user_id, date)
                    )
                ''')
                
                # User achievements
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS user_achievements (
                        user_id INTEGER,
                        achievement_id TEXT,
                        unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        PRIMARY KEY (user_id, achievement_id)
                    )
                ''')
                
                conn.commit()
                logger.info("✅ Reward database tables initialized")
                
        except Exception as e:
            logger.error(f"❌ Reward database initialization failed: {e}")
    
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
    
    def get_user_achievements(self, user_id: int) -> List[str]:
        """Get user's unlocked achievements"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute('''
                    SELECT achievement_id FROM user_achievements WHERE user_id = ?
                ''', (user_id,))
                
                return [row[0] for row in cursor.fetchall()]
                
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

def has_priority_processing(user_id: int, reward_db_instance) -> bool:
    """Check if user has priority processing active"""
    return reward_db_instance.has_active_reward(user_id, 'feature') and \
           any(r['id'] == 'priority_processing' for r in reward_db_instance.get_active_rewards(user_id))

def has_enhanced_voice_access(user_id: int, reward_db_instance, tier_handler) -> bool:
    """Check if user has enhanced voice chat V2 access (premium users get permanent access)"""
    # Premium users get permanent access
    if user_id in tier_handler.premium_users:
        return True
    
    # Non-premium users need the reward
    return reward_db_instance.has_active_reward(user_id, 'beta_feature') and \
           any(r['id'] == 'enhanced_voice_beta' for r in reward_db_instance.get_active_rewards(user_id))

# Global reward database instance (to be imported by main bot file)
reward_db = RewardDatabase()

