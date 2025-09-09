# import os, json, threading
# from typing import Dict, Any, Tuple
# import requests
# from utils.logger import logger
# import datetime

# # 구버전: _SECRETS_PATH = "secrets.json"
# _CONFIG_DIR = "config"
# _SECRETS_PATH = os.path.join(_CONFIG_DIR, "secrets.json")
# _OLD_SECRETS = "secrets.json"  # 루트 위치 (마이그레이션 용)
# _lock = threading.RLock()
# _REQUIRED_KEYS = ("APP_KEY", "APP_SECRET", "ACCOUNT_NO")

# PROD_BASE = "https://openapi.koreainvestment.com:9443"
# VTS_BASE = "https://openapivts.koreainvestment.com:29443"

# def _ensure_dir():
#     """config 디렉토리 생성"""
#     if not os.path.exists(_CONFIG_DIR):
#         os.makedirs(_CONFIG_DIR, exist_ok=True)

# def _migrate_if_needed():
#     """
#     기존 루트 secrets.json 존재 && 새 경로 없을 때 이동
#     """
#     if os.path.exists(_OLD_SECRETS) and not os.path.exists(_SECRETS_PATH):
#         try:
#             _ensure_dir()
#             logger.info(f"[SECRETS] 기존 {_OLD_SECRETS} -> {_SECRETS_PATH} 마이그레이션")
#             os.replace(_OLD_SECRETS, _SECRETS_PATH)
#         except Exception as e:
#             logger.warning(f"[SECRETS] 마이그레이션 실패: {e}")

# def load_secrets():
#     with _lock:
#         _migrate_if_needed()
#         if not os.path.exists(_SECRETS_PATH):
#             return {}
#         try:
#             with open(_SECRETS_PATH, encoding="utf-8") as f:
#                 return json.load(f)
#         except Exception as e:
#             logger.error(f"[SECRETS] JSON 파싱 실패: {e}")
#             return {}

# def save_secrets(data: dict):
#     with _lock:
#         _ensure_dir()
#         tmp = _SECRETS_PATH + ".tmp"
#         with open(tmp, "w", encoding="utf-8") as f:
#             json.dump(data, f, ensure_ascii=False, indent=2)
#         os.replace(tmp, _SECRETS_PATH)

# def _validate_secrets(secrets: dict):
#     missing = [k for k in _REQUIRED_KEYS if k not in secrets or not secrets[k]]
#     if missing:
#         raise RuntimeError(f"[SECRETS] 필수 키 누락: {missing}. config/secrets.json 작성 필요.")

# def _base_url(secrets: Dict[str, Any]) -> str:
#     """
#     기본값 운영(PROD). secrets에 USE_VTS=true 또는 ENV='vts'/'paper'면 VTS 사용.
#     BASE_URL이 명시되면 그 값 사용.
#     """
#     if "BASE_URL" in secrets and secrets["BASE_URL"]:
#         return str(secrets["BASE_URL"]).strip()
#     env = str(secrets.get("ENV", "")).lower()
#     use_vts = bool(secrets.get("USE_VTS")) or env in {"vts", "paper", "sandbox", "test"}
#     return VTS_BASE if use_vts else PROD_BASE

# def _shorten(txt: str, limit: int = 300) -> str:
#     if txt is None:
#         return ""
#     s = str(txt)
#     return s[:limit] + ("..." if len(s) > limit else "")

# def get_access_token():
#     """
#     KIS 액세스 토큰 발급
#     POST {BASE}/oauth2/tokenP
#     Content-Type: application/x-www-form-urlencoded
#     body: grant_type=client_credentials&appkey=...&appsecret=...
#     """
#     secrets: Dict[str, Any] = load_secrets()
#     _validate_secrets(secrets)
#     base = _base_url(secrets)
#     alt_base = VTS_BASE if base == PROD_BASE else PROD_BASE
#     headers = {"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"}
#     data = {
#         "grant_type": "client_credentials",
#         "appkey": secrets["APP_KEY"],
#         "appsecret": secrets["APP_SECRET"],
#     }
#     # 문서/환경별 경로 가변성 대응
#     token_paths = ["/oauth2/tokenP", "/oauth2/tokenp", "/oauth2/token"]

#     def do_req(b: str) -> Dict[str, Any]:
#         last_err: Exception | None = None
#         for p in token_paths:
#             url = f"{b}{p}"
#             r = requests.post(url, headers=headers, data=data, timeout=10)
#             if r.status_code < 400:
#                 return r.json()
#             try:
#                 j = r.json()
#                 msg = j.get("msg1") or j.get("msg") or _shorten(r.text)
#                 code = j.get("error_code") or j.get("rt_cd")
#             except Exception:
#                 msg, code = _shorten(r.text), None
#             logger.warning(f"[TOKEN] access_token 발급 실패 HTTP {r.status_code} {r.reason} base={b} path={p} msg={msg} code={code}")
#             last_err = requests.HTTPError(f"{r.status_code} {r.reason}", response=r)
#         # 모든 경로 실패 시 마지막 에러 전파
#         assert last_err is not None
#         raise last_err

#     try:
#         try:
#             logger.info(f"[TOKEN] access_token 발급 요청 base={base}")
#             resp = do_req(base)
#         except requests.HTTPError as e:
#             # 401/403/EGW00002 등 환경 불일치 시 반대 환경으로 1회 재시도
#             code = None
#             if getattr(e, "response", None) is not None:
#                 try:
#                     j = e.response.json()
#                     code = j.get("error_code") or j.get("rt_cd")
#                 except Exception:
#                     code = None
#             if getattr(e, "response", None) is not None and e.response.status_code in (401, 403) and alt_base != base:
#                 logger.info(f"[TOKEN] 환경 폴백 재시도 → base={alt_base} (code={code})")
#                 resp = do_req(alt_base)
#             else:
#                 raise
#         access_token = resp.get("access_token")
#         expires_in = resp.get("expires_in")
#         if not access_token:
#             msg = resp.get("msg1") or resp.get("msg") or ""
#             raise RuntimeError(f"access_token 없음(resp) msg={msg}")
#         logger.info("🔑 access_token 발급 완료")
#         return {"access_token": access_token, "expires_in": expires_in}
#     except requests.RequestException as e:
#         body = ""
#         if getattr(e, "response", None) is not None:
#             try:
#                 body = e.response.text
#             except Exception:
#                 body = ""
#         logger.warning(f"[TOKEN] access_token 발급 예외: {e} body={_shorten(body)}")
#         raise

# def get_websocket_access_key():
#     """
#     KIS WebSocket approval_key 발급
#     POST {BASE}/oauth2/approval
#     Content-Type: application/json
#     body: {"grant_type":"client_credentials","appkey":"...","appsecret":"...","secretkey":"..."}
#     """
#     secrets: Dict[str, Any] = load_secrets()
#     _validate_secrets(secrets)
#     base = _base_url(secrets)
#     alt_base = VTS_BASE if base == PROD_BASE else PROD_BASE
#     headers = {"Content-Type": "application/json; charset=UTF-8"}
#     body = {
#         "grant_type": "client_credentials",
#         "appkey": secrets["APP_KEY"],
#         "appsecret": secrets["APP_SECRET"],
#         "secretkey": secrets.get("APP_SECRET") or secrets.get("SECRET_KEY") or ""
#     }
#     approval_paths = ["/oauth2/approval", "/oauth2/Approval"]

#     def do_req(b: str) -> Dict[str, Any]:
#         last_err: Exception | None = None
#         for p in approval_paths:
#             url = f"{b}{p}"
#             r = requests.post(url, headers=headers, json=body, timeout=10)
#             if r.status_code < 400:
#                 return r.json()
#             try:
#                 j = r.json()
#                 msg = j.get("msg1") or j.get("msg") or _shorten(r.text)
#                 code = j.get("error_code") or j.get("rt_cd")
#             except Exception:
#                 msg, code = _shorten(r.text), None
#             logger.warning(f"[TOKEN] approval_key 발급 실패 HTTP {r.status_code} {r.reason} base={b} path={p} msg={msg} code={code}")
#             last_err = requests.HTTPError(f"{r.status_code} {r.reason}", response=r)
#         assert last_err is not None
#         raise last_err
#     try:
#         try:
#             logger.info(f"[TOKEN] approval_key 발급 요청 base={base}")
#             resp = do_req(base)
#         except requests.HTTPError as e:
#             code = None
#             if getattr(e, "response", None) is not None:
#                 try:
#                     j = e.response.json()
#                     code = j.get("error_code") or j.get("rt_cd")
#                 except Exception:
#                     code = None
#             if getattr(e, "response", None) is not None and e.response.status_code in (401, 403) and alt_base != base:
#                 logger.info(f"[TOKEN] 환경 폴백 재시도 → base={alt_base} (code={code})")
#                 resp = do_req(alt_base)
#             else:
#                 raise
#         key = resp.get("approval_key")
#         if not key:
#             msg = resp.get("msg1") or resp.get("msg") or ""
#             raise RuntimeError(f"approval_key 없음(resp) msg={msg}")
        
#         logger.info(f"[TOKEN] 새 approval_key: {key[:16]}...")
#         logger.info("🔑 approval_key 발급 완료")
        
#         # status 파일 저장 (중요!)
#         _ensure_dir()
#         status_path = os.path.join(_CONFIG_DIR, "websocket_access_key_status.json")
#         status = {
#             "approval_key": key,
#             "timestamp": datetime.datetime.now().isoformat(),
#             "approval_key_issued_at": datetime.datetime.now().isoformat()
#         }
#         with open(status_path, "w", encoding="utf-8") as f:
#             json.dump(status, f, ensure_ascii=False, indent=2)
#         logger.info(f"[TOKEN] ws_key_status 저장 완료 path={status_path}")
        
#         return key
#     except requests.RequestException as e:
#         body = ""
#         if getattr(e, "response", None) is not None:
#             try:
#                 body = e.response.text
#             except Exception:
#                 body = ""
#         logger.warning(f"[TOKEN] approval_key 발급 예외: {e} body={_shorten(body)}")
#         raise