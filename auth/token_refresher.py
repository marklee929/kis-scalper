# # filepath: c:\WORK\kis-scalper\auth\token_refresher.py
# from __future__ import annotations
# import os, json, time, threading
# from datetime import datetime, timedelta
# from typing import Optional, Callable, Any, Dict

# from utils.logger import logger
# from auth.token_manager import get_access_token, get_websocket_access_key

# DEFAULT_REFRESH_MARGIN_SEC = 60
# WEBSOCKET_KEY_TTL_HOURS = 12
# REFRESH_LOOP_INTERVAL = 30

# TOKEN_STATUS_PATH = os.path.join("config", "token_status.json")
# WS_KEY_STATUS_PATH = os.path.join("config", "websocket_access_key_status.json")

# def _now_iso() -> str:
#     return datetime.utcnow().isoformat()

# def _load_json(path: str) -> Dict[str, Any]:
#     try:
#         if not os.path.exists(path):
#             return {}
#         with open(path, "r", encoding="utf-8") as f:
#             return json.load(f) or {}
#     except Exception:
#         return {}

# def _save_json(path: str, data: Dict[str, Any]) -> None:
#     os.makedirs(os.path.dirname(path), exist_ok=True)
#     tmp = path + ".tmp"
#     with open(tmp, "w", encoding="utf-8") as f:
#         json.dump(data, f, ensure_ascii=False, indent=2)
#     os.replace(tmp, path)

# def load_token_status() -> Dict[str, Any]:
#     return _load_json(TOKEN_STATUS_PATH)

# def save_token_status(data: Dict[str, Any]) -> None:
#     _save_json(TOKEN_STATUS_PATH, data)
#     tok = str(data.get("access_token", ""))[:10]
#     exp = data.get("access_token_expire_at", "")
#     logger.info(f"[TOKEN] token_status 저장 완료 path={TOKEN_STATUS_PATH} token~={tok} exp={exp}")

# def load_ws_key_status() -> Dict[str, Any]:
#     return _load_json(WS_KEY_STATUS_PATH)

# def save_ws_key_status(data: Dict[str, Any]) -> None:
#     _save_json(WS_KEY_STATUS_PATH, data)
#     logger.info(f"[TOKEN] ws_key_status 저장 완료 path={WS_KEY_STATUS_PATH}")

# class TokenContext:
#     def __init__(self):
#         self._lock = threading.RLock()
#         self.access_token: Optional[str] = None
#         self.token_expire_at: Optional[datetime] = None
#         self._approval_key: Optional[str] = None
#         self.approval_key_issued_at: Optional[datetime] = None
#         self.on_approval_refresh: Optional[Callable[[str], None]] = None
#         self.on_access_refresh: Optional[Callable[[str], None]] = None
#         self._stop_event = threading.Event()

#     def snapshot(self) -> dict:
#         with self._lock:
#             return {
#                 "access_token": self.access_token,
#                 "token_expire_at": self.token_expire_at,
#                 "approval_key": self.approval_key,
#                 "approval_key_issued_at": self.approval_key_issued_at
#             }

#     def set_access(self, token: str, expire_at: Optional[datetime]) -> None:
#         with self._lock:
#             self.access_token = token
#             self.token_expire_at = expire_at

#     @property
#     def approval_key(self) -> Optional[str]:
#         return self._approval_key

#     def set_approval(self, key: str) -> None:
#         self._approval_key = key
#         with self._lock:
#             self.approval_key_issued_at = datetime.utcnow()

#     def needs_access_refresh(self, margin: int = DEFAULT_REFRESH_MARGIN_SEC) -> bool:
#         with self._lock:
#             tok = (self.access_token or "").strip().upper()
#             if not tok or tok in {"DUMMY", "DUMMY_TOKEN"}:
#                 return True
#             if not self.token_expire_at:
#                 return True
#             return (self.token_expire_at - datetime.utcnow()).total_seconds() < margin

# def parse_expire_at(token_resp: Dict[str, Any]) -> Optional[datetime]:
#     if not token_resp:
#         return None
#     expires_in = token_resp.get("expires_in")
#     if expires_in is None:
#         return None
#     try:
#         seconds = int(str(expires_in))
#     except (TypeError, ValueError):
#         return None
#     return datetime.utcnow() + timedelta(seconds=seconds)

# def _is_different_date(issued_at: datetime) -> bool:
#     """
#     발급일과 현재일이 다른지 확인 (KIS approval_key는 날짜 기준)
#     """
#     now = datetime.utcnow()
#     issued_date = issued_at.date()
#     current_date = now.date()
#     return issued_date != current_date

# def init_tokens(ctx: TokenContext) -> None:
#     """초기 토큰 발급/로드"""
#     # access_token 처리 (기존)
#     tstat = load_token_status()
#     token = tstat.get("access_token")
#     expire_iso = tstat.get("access_token_expire_at")
#     expire_at: Optional[datetime] = None
#     if expire_iso:
#         try:
#             expire_at = datetime.fromisoformat(expire_iso)
#         except Exception:
#             expire_at = None

#     need_issue = (not token) or (str(token).strip().upper() in {"DUMMY", "DUMMY_TOKEN"}) or (expire_at is None) or (
#         expire_at and (expire_at - datetime.utcnow()).total_seconds() < DEFAULT_REFRESH_MARGIN_SEC
#     )
#     if need_issue:
#         logger.info("[TOKEN] 초기 access_token 발급/갱신(status.json)")
#         new_resp = get_access_token()
#         token = new_resp.get("access_token") if isinstance(new_resp, dict) else new_resp
#         expire_at = parse_expire_at(new_resp) if isinstance(new_resp, dict) else None
#         if not token:
#             raise RuntimeError("access_token 발급 실패")
#         tstat["access_token"] = token
#         if expire_at:
#             tstat["access_token_expire_at"] = expire_at.isoformat()
#         tstat["timestamp"] = _now_iso()
#         save_token_status(tstat)
#     if not isinstance(token, str) or not token:
#         raise RuntimeError("access_token 미확보(token_status.json 확인 필요)")
#     ctx.set_access(token, expire_at)
#     if ctx.on_access_refresh:
#         try:
#             ctx.on_access_refresh(token)
#         except Exception as cb_e:
#             logger.debug(f"[TOKEN] access refresh 콜백 오류(초기): {cb_e}")

#     # approval key (날짜 기준으로 수정)
#     wstat = load_ws_key_status()
#     approval_key = wstat.get("approval_key")
#     issued_iso = wstat.get("approval_key_issued_at") or wstat.get("timestamp")
#     issued_at: Optional[datetime] = None
#     if issued_iso:
#         try:
#             issued_at = datetime.fromisoformat(issued_iso)
#         except Exception:
#             issued_at = None

#     # KIS approval_key는 날짜가 바뀌면 무조건 새로 발급
#     need_ws_issue = (
#         (not approval_key) or 
#         (issued_at is None) or 
#         _is_different_date(issued_at)
#     )
    
#     if need_ws_issue and issued_at:
#         logger.info(f"[TOKEN] approval_key 날짜 변경 감지: 발급일={issued_at.date()} 현재일={datetime.utcnow().date()}")
    
#     if need_ws_issue:
#         logger.info("[TOKEN] 초기 approval_key 발급/갱신(ws status.json)")
#         key = get_websocket_access_key()
#         if not key:
#             raise RuntimeError("approval_key 발급 실패")
#         approval_key = key
#         wstat["approval_key"] = key
#         wstat["approval_key_issued_at"] = _now_iso()
#         save_ws_key_status(wstat)
#     if not isinstance(approval_key, str) or not approval_key:
#         raise RuntimeError("approval_key 미확보(websocket_access_key_status.json 확인 필요)")
#     ctx.set_approval(approval_key)

# def ensure_fresh_access_token(ctx: TokenContext) -> None:
#     if ctx.needs_access_refresh():
#         logger.info("[TOKEN] 동기 갱신 수행(status.json)")
#         new_resp = get_access_token()
#         token = new_resp.get("access_token") if isinstance(new_resp, dict) else new_resp
#         expire_at = parse_expire_at(new_resp) if isinstance(new_resp, dict) else None
#         if token:
#             tstat = load_token_status()
#             tstat["access_token"] = token
#             if expire_at:
#                 tstat["access_token_expire_at"] = expire_at.isoformat()
#             tstat["timestamp"] = _now_iso()
#             save_token_status(tstat)
#             ctx.set_access(token, expire_at)
#             if ctx.on_access_refresh:
#                 try:
#                     ctx.on_access_refresh(token)
#                 except Exception as cb_e:
#                     logger.debug(f"[TOKEN] access refresh 콜백 오류(동기): {cb_e}")

# def _should_refresh_approval_key(ctx: TokenContext) -> bool:
#     """
#     approval_key 갱신 필요 여부 판단
#     - 날짜가 바뀌면 무조건 갱신 (KIS 정책)
#     - 키가 없거나 파일이 없으면 갱신
#     """
#     try:
#         status_path = os.path.join("config", "websocket_access_key_status.json")
#         if not os.path.exists(status_path):
#             logger.info("[TOKEN] approval_key status 파일 없음 → 갱신 필요")
#             return True
            
#         with open(status_path, encoding="utf-8") as f:
#             data = json.load(f)
            
#         issued_str = data.get("approval_key_issued_at")
#         if not issued_str:
#             logger.info("[TOKEN] approval_key_issued_at 없음 → 갱신 필요")
#             return True
            
#         issued = datetime.fromisoformat(issued_str)
        
#         # 날짜 기준 체크 (KIS approval_key는 날짜가 바뀌면 무조건 갱신)
#         if _is_different_date(issued):
#             logger.info(f"[TOKEN] approval_key 날짜 변경: 발급일={issued.date()} 현재일={datetime.utcnow().date()} → 갱신 필요")
#             return True
            
#         return False
        
#     except Exception as e:
#         logger.warning(f"[TOKEN] approval_key 만료 체크 실패: {e} → 갱신 필요")
#         return True

# def _refresh_approval_key_if_needed(ctx: TokenContext) -> None:
#     """approval_key 갱신 (필요시만)"""
#     if not _should_refresh_approval_key(ctx):
#         return
        
#     try:
#         logger.info("[TOKEN] approval_key 갱신 시작")
#         new_key = get_websocket_access_key()
#         ctx.set_approval(new_key)      # 올바른 메서드명
#         logger.info("[TOKEN] approval_key 갱신 완료")
#     except Exception as e:
#         logger.error(f"[TOKEN] approval_key 갱신 실패: {e}")

# def _refresh_loop(ctx: TokenContext) -> None:
#     """백그라운드 토큰 갱신 루프"""
#     while not ctx._stop_event.is_set():
#         try:
#             # access_token 갱신 (기존)
#             if ctx.needs_access_refresh():
#                 logger.info("[TOKEN] 만료 임박 → access_token 갱신(status.json)")
#                 new_resp = get_access_token()
#                 token: Optional[str] = new_resp.get("access_token") if isinstance(new_resp, dict) else new_resp
#                 expire_at: Optional[datetime] = parse_expire_at(new_resp) if isinstance(new_resp, dict) else None
#                 if token:
#                     tstat = load_token_status()
#                     tstat["access_token"] = token
#                     if expire_at:
#                         tstat["access_token_expire_at"] = expire_at.isoformat()
#                     tstat["timestamp"] = _now_iso()
#                     save_token_status(tstat)
#                     ctx.set_access(token, expire_at)
#                     if ctx.on_access_refresh:
#                         try:
#                             ctx.on_access_refresh(token)
#                         except Exception as cb_e:
#                             logger.debug(f"[TOKEN] access refresh 콜백 오류: {cb_e}")
#                     logger.info("[TOKEN] access_token 갱신 완료")
#                 else:
#                     logger.warning("[TOKEN] access_token 갱신 실패(토큰 없음)")

#             # approval_key 갱신 (새로운 통합 방식)
#             _refresh_approval_key_if_needed(ctx)
                
#         except Exception as e:
#             logger.error(f"[TOKEN] 갱신 루프 오류: {e}")
            
#         # 10분마다 체크
#         ctx._stop_event.wait(REFRESH_LOOP_INTERVAL)

# def start_token_refresher(
#     ctx: TokenContext,
#     interval: int = REFRESH_LOOP_INTERVAL,
#     stop_event: Optional[threading.Event] = None
# ) -> threading.Thread:
#     th = threading.Thread(target=_refresh_loop, args=(ctx,), daemon=True)
#     th.start()
#     return th

