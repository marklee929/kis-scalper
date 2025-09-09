import os
import json
from typing import Dict, Any
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class Config:
    """설정 관리자 - 기존 secrets.json 연동"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent  # core -> kis-scalper
        self.secrets_file = self.project_root / "config" / "secrets.json"
        self.balance_file = self.project_root / "config" / "balance.json"
        self._config = self._load_secrets()

    def _load_balance(self) -> float:
        """balance.json에서 초기 잔고를 로드합니다."""
        try:
            if self.balance_file.exists():
                with open(self.balance_file, 'r', encoding='utf-8') as f:
                    balance_data = json.load(f)
                balance = float(balance_data.get("available_cash", 0))
                logger.info(f"[CONFIG] balance.json에서 초기 잔고 로드: {balance:,.0f}원")
                return balance
            return 0
        except Exception as e:
            logger.error(f"[CONFIG] balance.json 로드 실패: {e}")
            return 0
    
    def _load_secrets(self) -> Dict[str, Any]:
        """기존 secrets.json 로드"""
        try:
            if self.secrets_file.exists():
                with open(self.secrets_file, 'r', encoding='utf-8') as f:
                    secrets = json.load(f)
                
                logger.info("[CONFIG] secrets.json 로드 성공")
                
                # secrets.json -> 시스템 포맷 변환
                config = {
                    "api": {
                        "app_key": secrets.get("APP_KEY", ""),
                        "app_secret": secrets.get("APP_SECRET", ""),
                        "account_no": secrets.get("ACCOUNT_NO", ""),
                        "environment": secrets.get("ENVIRONMENT", "DEMO"),
                        "custtype": secrets.get("CUSTTYPE", "P")
                    },
                    "telegram": {
                        "bot_token": secrets.get("TELEGRAM_TOKEN", ""),
                        "chat_id": secrets.get("TELEGRAM_CHAT_ID", "")
                    },
                    "trading": {
                        "budget": self._load_balance() or int(secrets.get("BUDGET", 1000000)),  # balance.json 우선, 없으면 secrets.json
                        "max_positions": 5,
                        "max_daily_loss_pct": -5.0,
                        "position_size_pct": 2.0,
                        "stop_loss_pct": -0.8,
                        "take_profit_pct": 1.5,
                        "position_sizing_method": "dynamic",
                        "enable_boot_mode_trading": True, # True: 장초반 즉시 거래, False: N분 후 거래
                        "boot_mode_duration_min": 5,      # 부트 모드 지속 시간 (분)
                        "initial_data_wait_min": 10       # 부트 모드 비활성 시 데이터 축적 대기 시간 (분)
                    },
                    "system": {
                        "log_level": "INFO",
                        "health_check_interval": 300,
                        "backup_interval": 3600
                    }
                }
                
                return config
            else:
                logger.critical(f"CRITICAL: secrets.json 파일을 찾을 수 없습니다. 경로: {self.secrets_file}")
                raise FileNotFoundError(f"secrets.json not found at {self.secrets_file}")
                
        except Exception as e:
            logger.error(f"[CONFIG] 설정 로드 실패: {e}")
            return self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """기본 설정 반환"""
        return {
            "api": {"app_key": "", "app_secret": "", "account_no": ""},
            "telegram": {"bot_token": "", "chat_id": ""},
            "trading": {"budget": 1000000, "max_positions": 5}
        }
    
    def get(self, key: str, default=None):
        """설정 값 조회 (점 표기법 지원)"""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def get_kis_config(self) -> Dict:
        """KIS API 설정 반환"""
        return self._config.get("api", {})
    
    def get_telegram_config(self) -> Dict:
        """텔레그램 설정 반환"""
        return self._config.get("telegram", {})
    
    def get_trading_config(self) -> Dict:
        """거래 설정 반환"""
        return self._config.get("trading", {})
    
    def is_real_trading(self) -> bool:
        """실거래 모드 여부"""
        return self.get("api.environment", "DEMO") == "REAL"
    
    def is_telegram_enabled(self) -> bool:
        """텔레그램 활성화 여부"""
        telegram_config = self.get_telegram_config()
        return bool(telegram_config.get('bot_token') and telegram_config.get('chat_id'))
    
    def print_config_summary(self):
        """설정 요약 출력"""
        print("\n" + "="*60)
        print("KIS 스캘핑 시스템 설정 정보")
        print("="*60)
        
        # KIS API 설정
        api_config = self.get_kis_config()
        print(f"KIS API 연결:")
        print(f"  * APP_KEY: {api_config.get('app_key', 'N/A')[:15]}...")
        print(f"  * 계좌번호: {api_config.get('account_no', 'N/A')}")
        
        env_status = "실거래" if self.is_real_trading() else "모의투자"
        print(f"  * 환경: {env_status} ({api_config.get('environment', 'N/A')})")
        
        # 텔레그램 설정  
        telegram_status = "활성화" if self.is_telegram_enabled() else "비활성화"
        print(f"텔레그램 알림: {telegram_status}")
        
        if self.is_telegram_enabled():
            telegram_config = self.get_telegram_config()
            print(f"  * CHAT_ID: {telegram_config.get('chat_id', 'N/A')}")
        
        # 거래 설정
        trading_config = self.get_trading_config()
        print(f"거래 설정:")
        print(f"  * 예산: {trading_config.get('budget', 0):,}원")
        print(f"  * 최대 포지션: {trading_config.get('max_positions', 0)}개")
        print(f"  * 일일 손실 한도: {trading_config.get('max_daily_loss_pct', 0)}%")
        print(f"  * 포지션 크기: {trading_config.get('position_size_pct', 0)}%")
        
        print("="*60 + "\n")

# 전역 설정 인스턴스
config = Config()
