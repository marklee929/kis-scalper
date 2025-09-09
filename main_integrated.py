# filepath: c:\WORK\kis-scalper\main_integrated.py
"""
KIS 스캘핑 통합 시스템 - 최종 실행 파일 (config 경로 수정)
"""
import argparse
import sys
from pathlib import Path

# 프로젝트 루트를 Python path에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 프로젝트 로거 설정
from utils.logger import logger

# 데이터 로거 임포트 및 종료 시 저장되도록 등록
try:
    from data.data_logger import data_logger
    import atexit
    atexit.register(data_logger.save_to_file)
    logger.info("[MAIN] 데이터 로거 활성화 및 종료 시 자동 저장 등록")
except ImportError:
    logger.warning("[MAIN] 데이터 로거를 찾을 수 없어, 실시간 데이터 저장이 비활성화됩니다.")


def main():
    """메인 실행 함수"""
    print("KIS 스캘핑 통합 시스템 v6.0")
    print("=" * 50)
    
    # Add argument parsing
    parser = argparse.ArgumentParser(description="KIS Scalping Integrated System")
    parser.add_argument("--summary", "-s", action="store_true", help="Print trade summary and exit.")
    parser.add_argument("--date", type=str, help="Date for the summary in YYYY-MM-DD format.")
    args = parser.parse_args()

    try:
        # core에서 통합 시스템과 config 임포트
        from core.integrated_trading_system import IntegratedTradingSystem, load_config
        from core.config import config
        
        # 설정 로드
        system_config = load_config()
        logger.info("[MAIN] 설정 로드 완료")
        
        # 통합 시스템 생성
        trading_system = IntegratedTradingSystem(system_config)

        if args.summary:
            # If --summary argument is present, print summary and exit
            trading_system.print_summary(date_str=args.date)
            return True # Indicate success for clean exit
        
        # 실거래 경고 (자동화용으로 주석 처리 가능)
        if config.is_real_trading():
            print("실거래 모드 활성화됨")
            print(f"거래 예산: {config.get('trading.budget'):,}원")
            # 자동 실행용: 확인 프롬프트 비활성화
            # response = input("실제 거래를 시작하시겠습니까? (yes/no): ")
            # if response.lower() not in ['yes', 'y']:
            #     print("거래가 취소되었습니다.")
            #     return False
        else:
            print("모의투자 모드")
        
        # 시작 메시지
        logger.info("[MAIN] === KIS 스캘핑 시스템 Phase 1~6 통합 ===")
        logger.info("[MAIN] • Phase 1: 실시간 신호 생성")
        logger.info("[MAIN] • Phase 2: 종목 선별")
        logger.info("[MAIN] • Phase 3: 포지션 관리")
        logger.info("[MAIN] • Phase 4: 시간대별 전략")
        logger.info("[MAIN] • Phase 5: 백테스팅 & 성과 분석")
        logger.info("[MAIN] • Phase 6: 실시간 통합 운영")
        
        # 시스템 실행
        success = trading_system.run()
        
        if success:
            logger.info("[MAIN] 시스템 정상 종료")
        else:
            logger.error("[MAIN] 시스템 비정상 종료")
        
        return success
        
    except ImportError as e:
        logger.error(f"[MAIN] 모듈 임포트 실패: {e}")
        return False
        
    except Exception as e:
        logger.error(f"[MAIN] 실행 중 오류: {e}")
        return False
    
    finally:
        logger.info("[MAIN] 프로그램 종료")

if __name__ == "__main__":
    try:
        success = main()
        exit_code = 0 if success else 1
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("[MAIN] 사용자 중단")
        sys.exit(0)
    except Exception as e:
        logger.error(f"[MAIN] 처리되지 않은 예외: {e}")
        sys.exit(1)