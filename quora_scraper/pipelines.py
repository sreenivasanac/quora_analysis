import logging
from .database import DatabaseManager
from .items import QuoraAnswerItem

logger = logging.getLogger(__name__)


class PostgreSQLPipeline:
    """Pipeline to store scraped items in PostgreSQL database"""
    
    def __init__(self):
        self.db_manager = None
        self.items_processed = 0
        
    def open_spider(self, spider):
        """Initialize database connection when spider opens"""
        try:
            self.db_manager = DatabaseManager()
            self.db_manager.connect()
            self.db_manager.create_tables()
            logger.info("PostgreSQL pipeline initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize PostgreSQL pipeline: {e}")
            raise
    
    def close_spider(self, spider):
        """Close database connection when spider closes"""
        if self.db_manager:
            self.db_manager.disconnect()
        logger.info(f"PostgreSQL pipeline closed. Total items processed: {self.items_processed}")
    
    def process_item(self, item, spider):
        """Process and store item in database"""
        if not isinstance(item, QuoraAnswerItem):
            return item
        
        try:
            # For now, we're only storing answer links as per prompt.txt requirements
            answered_question_url = item.get('answered_question_url')
            
            if answered_question_url:
                # Check if the answer already exists
                if not self.db_manager.check_answer_exists(answered_question_url):
                    item_id = self.db_manager.insert_answer_link(answered_question_url)
                    item['id'] = item_id
                    self.items_processed += 1
                    
                    # Log progress every 100 answers
                    if self.items_processed % 100 == 0:
                        total_count = self.db_manager.get_answer_count()
                        logger.info(f"Progress: {self.items_processed} new answers processed. Total in DB: {total_count}")
                else:
                    logger.debug(f"Answer already exists: {answered_question_url}")
            
            return item
            
        except Exception as e:
            logger.error(f"Error processing item: {e}")
            logger.error(f"Item data: {dict(item)}")
            return item 