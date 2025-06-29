import scrapy

class QuoraAnswerItem(scrapy.Item):
    """Item for storing Quora answer data"""
    id = scrapy.Field()
    question_url = scrapy.Field()
    answered_question_url = scrapy.Field()
    question_text = scrapy.Field()
    answer_content = scrapy.Field()
    revision_link = scrapy.Field()
    post_timestamp_raw = scrapy.Field()
    post_timestamp_parsed = scrapy.Field() 