# filepath: c:/WORK/kis-scalper/utils/notifier.py
import requests
from core.config import config  # 프로젝트의 중앙 설정 객체 사용
from utils.logger import logger

class TelegramNotifier:
    """
    텔레그램 메시지 발송을 위한 싱글턴 클래스.
    requests 라이브러리를 사용하여 간단하게 구현.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TelegramNotifier, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        
        telegram_config = config.get_telegram_config()
        telegram_config = config.get_telegram_config()
        self.token = telegram_config.get('bot_token')
        self.chat_id = telegram_config.get('chat_id')
        
        self.is_enabled = bool(self.token and self.chat_id)
        
        if self.is_enabled:
            logger.info("[Notifier] 텔레그램 알림 기능 활성화.")
        else:
            logger.warning("[Notifier] 텔레그램 설정(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)이 없어 알림 기능이 비활성화됩니다.")
            
        self._initialized = True

    def send_message(self, message: str, silent: bool = False) -> bool:
        """
        텔레그램으로 메시지를 발송합니다.

        :param message: 보낼 메시지
        :param silent: 사용자에게 소리 없는 알림을 보낼지 여부
        :return: 성공 여부
        """
        if not self.is_enabled:
            return False

        # Markdown 특수문자 이스케이프 처리
        escape_chars = '_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!'
        for char in escape_chars:
            message = message.replace(char, f'\\{char}')

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            'chat_id': self.chat_id,
            'text': message,
            'disable_notification': silent,
            'parse_mode': 'MarkdownV2'
        }
        
        try:
            response = requests.post(url, json=payload, timeout=5)
            response.raise_for_status()
            logger.debug(f"[Notifier] 텔레그램 메시지 발송 성공: {message}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"[Notifier] 텔레그램 메시지 발송 실패: {e}")
            return False

# 싱글턴 인스턴스 생성
notifier = TelegramNotifier()
