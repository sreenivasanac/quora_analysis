import os
import psycopg2
import psycopg2.extras
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages PostgreSQL database connections and operations"""
    
    def __init__(self, database_url: Optional[str] = None):
        self.database_url = database_url or os.getenv('DATABASE_URL')
        if not self.database_url:
            raise ValueError("DATABASE_URL environment variable is required")
        
        self.connection = None
        self.cursor = None
    
    def connect(self):
        """Establish database connection"""
        try:
            self.connection = psycopg2.connect(self.database_url)
            self.cursor = self.connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
            logger.info("Connected to PostgreSQL database")
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        logger.info("Disconnected from PostgreSQL database")
    
    def create_tables(self):
        """Create the quora_answers table if it doesn't exist"""
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS quora_answers (
            id SERIAL PRIMARY KEY,
            question_url TEXT,
            answered_question_url TEXT,
            question_text TEXT,
            answer_content TEXT,
            revision_link TEXT,
            post_timestamp_raw TEXT,
            post_timestamp_parsed TIMESTAMP NULL
        );
        
        CREATE INDEX IF NOT EXISTS idx_answered_question_url 
        ON quora_answers(answered_question_url);
        """
        
        try:
            self.cursor.execute(create_table_sql)
            self.connection.commit()
            logger.info("Database tables created/verified successfully")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            self.connection.rollback()
            raise
    
    def insert_answer_link(self, answered_question_url: str) -> int:
        """Insert a new answer link and return the ID"""
        insert_sql = """
        INSERT INTO quora_answers (answered_question_url) 
        VALUES (%s) 
        RETURNING id;
        """
        
        try:
            self.cursor.execute(insert_sql, (answered_question_url,))
            result = self.cursor.fetchone()
            self.connection.commit()
            return result['id']
        except Exception as e:
            logger.error(f"Failed to insert answer link: {e}")
            self.connection.rollback()
            raise
    
    def check_answer_exists(self, answered_question_url: str) -> bool:
        """Check if an answer URL already exists in the database"""
        check_sql = "SELECT id FROM quora_answers WHERE answered_question_url = %s;"
        
        try:
            self.cursor.execute(check_sql, (answered_question_url,))
            return self.cursor.fetchone() is not None
        except Exception as e:
            logger.error(f"Failed to check answer existence: {e}")
            return False
    
    def get_answer_count(self) -> int:
        """Get the total count of answers in the database"""
        count_sql = "SELECT COUNT(*) as count FROM quora_answers;"
        
        try:
            self.cursor.execute(count_sql)
            result = self.cursor.fetchone()
            return result['count']
        except Exception as e:
            logger.error(f"Failed to get answer count: {e}")
            return 0
    
    def get_all_answer_urls(self) -> set:
        """Get all existing answered_question_url values from database"""
        select_sql = "SELECT answered_question_url FROM quora_answers WHERE answered_question_url IS NOT NULL;"
        
        try:
            self.cursor.execute(select_sql)
            results = self.cursor.fetchall()
            
            url_set = set()
            for row in results:
                if row['answered_question_url']:
                    url_set.add(row['answered_question_url'])
            
            logger.info(f"Retrieved {len(url_set)} existing URLs from database")
            return url_set
            
        except Exception as e:
            logger.error(f"Failed to get existing URLs from database: {e}")
            return set()

    def get_incomplete_entries(self, limit: int = None) -> list:
        """Get entries that need to be processed (missing question_text or answer_content)"""
        select_sql = """
        SELECT id, answered_question_url 
        FROM quora_answers 
        WHERE answered_question_url IS NOT NULL 
        AND (question_text IS NULL OR answer_content IS NULL)
        ORDER BY id
        """
        
        if limit:
            select_sql += f" LIMIT {limit}"
        
        try:
            self.cursor.execute(select_sql)
            results = self.cursor.fetchall()
            
            entries = []
            for row in results:
                entries.append({
                    'id': row['id'],
                    'answered_question_url': row['answered_question_url']
                })
            
            logger.info(f"Retrieved {len(entries)} incomplete entries from database")
            return entries
            
        except Exception as e:
            logger.error(f"Failed to get incomplete entries from database: {e}")
            return []
    
    def update_answer_data(self, answered_question_url: str, question_url: str = None, 
                          question_text: str = None, answer_content: str = None,
                          revision_link: str = None, post_timestamp_raw: str = None,
                          post_timestamp_parsed = None) -> bool:
        """Update answer data for a specific answered_question_url"""
        
        # Build dynamic update query based on provided fields
        update_fields = []
        values = []
        
        if question_url is not None:
            update_fields.append("question_url = %s")
            values.append(question_url)
        
        if question_text is not None:
            update_fields.append("question_text = %s")
            values.append(question_text)
        
        if answer_content is not None:
            update_fields.append("answer_content = %s")
            values.append(answer_content)
        
        if revision_link is not None:
            update_fields.append("revision_link = %s")
            values.append(revision_link)
        
        if post_timestamp_raw is not None:
            update_fields.append("post_timestamp_raw = %s")
            values.append(post_timestamp_raw)
        
        if post_timestamp_parsed is not None:
            update_fields.append("post_timestamp_parsed = %s")
            values.append(post_timestamp_parsed)
        
        if not update_fields:
            logger.warning("No fields to update")
            return False
        
        update_sql = f"""
        UPDATE quora_answers 
        SET {', '.join(update_fields)}
        WHERE answered_question_url = %s
        """
        values.append(answered_question_url)
        
        try:
            self.cursor.execute(update_sql, values)
            self.connection.commit()
            
            if self.cursor.rowcount > 0:
                logger.debug(f"Updated answer data for: {answered_question_url}")
                return True
            else:
                logger.warning(f"No row updated for URL: {answered_question_url}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to update answer data: {e}")
            self.connection.rollback()
            return False
    
    def get_incomplete_count(self) -> int:
        """Get count of entries that need processing"""
        count_sql = """
        SELECT COUNT(*) as count 
        FROM quora_answers 
        WHERE answered_question_url IS NOT NULL 
        AND (question_text IS NULL OR answer_content IS NULL)
        """
        
        try:
            self.cursor.execute(count_sql)
            result = self.cursor.fetchone()
            return result['count']
        except Exception as e:
            logger.error(f"Failed to get incomplete count: {e}")
            return 0


 