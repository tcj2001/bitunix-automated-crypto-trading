from datetime import datetime
import pytz
from logger import Logger

class NotificationManager:
    def __init__(self, logger, max_size=100):
        self.max_size = max_size
        self.notifications = []
        self.logger = logger

    def add_notification(self, notification):
        # Add the new notification at the top
        timezone = pytz.timezone('America/Chicago')
        timestamp = datetime.now(timezone).strftime('%Y-%m-%d %H:%M:%S')
        self.notifications.insert(0, f'({timestamp}) {notification}')
        self.logger.info(f'({timestamp}) {notification}')
        # Ensure the list doesn't exceed the maximum size
        if len(self.notifications) > self.max_size:
            self.notifications.pop()

    def get_notifications(self):
        return self.notifications

