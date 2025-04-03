from datetime import datetime
import pytz
from logger import Logger
logger = Logger(__name__).get_logger()

class NotificationManager:
    def __init__(self, max_size=100):
        self.max_size = max_size
        self.notifications = []

    def add_notification(self, notification):
        # Add the new notification at the top
        timezone = pytz.timezone('America/Chicago')
        timestamp = datetime.now(timezone).strftime('%Y-%m-%d %H:%M:%S')
        self.notifications.insert(0, f'({timestamp}) {notification}')
        logger.info(f'({timestamp}) {notification}')
        # Ensure the list doesn't exceed the maximum size
        if len(self.notifications) > self.max_size:
            self.notifications.pop()

    def get_notifications(self):
        return self.notifications

