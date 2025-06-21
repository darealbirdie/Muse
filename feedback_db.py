import aiosqlite
from datetime import datetime
import os

class FeedbackDB:
    def __init__(self, db_path: str = "feedback.db"):
        self.db_path = db_path
    
    async def initialize(self):
        """Create the feedback table"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT NOT NULL,
                    rating INTEGER NOT NULL CHECK (rating >= 1 AND rating <= 5),
                    message TEXT,
                    created_at TEXT NOT NULL
                )
            ''')
            await db.commit()
            print("✅ Feedback database initialized!")
    
    async def add_feedback(self, user_id: int, username: str, rating: int, message: str = None):
        """Add feedback to database"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('''
                INSERT INTO feedback (user_id, username, rating, message, created_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (user_id, username, rating, message, datetime.now().isoformat()))
            await db.commit()
    
    async def get_all_feedback(self, limit: int = 50):
        """Get all feedback"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT username, rating, message, created_at
                FROM feedback
                ORDER BY created_at DESC
                LIMIT ?
            ''', (limit,))
            rows = await cursor.fetchall()
            
            return [{
                "username": row[0],
                "rating": row[1],
                "message": row[2],
                "created_at": row[3]
            } for row in rows]
    
    async def get_stats(self):
        """Get feedback statistics"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute('''
                SELECT 
                    COUNT(*) as total,
                    AVG(rating) as avg_rating,
                    COUNT(CASE WHEN rating = 5 THEN 1 END) as five_star,
                    COUNT(CASE WHEN rating = 4 THEN 1 END) as four_star,
                    COUNT(CASE WHEN rating = 3 THEN 1 END) as three_star,
                    COUNT(CASE WHEN rating = 2 THEN 1 END) as two_star,
                    COUNT(CASE WHEN rating = 1 THEN 1 END) as one_star
                FROM feedback
            ''')
            row = await cursor.fetchone()
            
            return {
                "total": row[0],
                "avg_rating": round(row[1], 1) if row[1] else 0,
                "five_star": row[2],
                "four_star": row[3],
                "three_star": row[4],
                "two_star": row[5],
                "one_star": row[6]
            }
    # Add these methods to your feedback_db class:

    async def get_last_feedback_date(self, user_id: int) -> str:
        """Get the date of user's last feedback"""
        pass

    async def get_last_feedback_session(self, user_id: int) -> int:
        """Get session count when user last gave feedback"""
        pass

    async def add_feedback(self, user_id: int, username: str, rating: int, 
                      message: str = None, session_count: int = 0):
        """Add feedback with session tracking"""
        pass

# Create instance
feedback_db = FeedbackDB()

