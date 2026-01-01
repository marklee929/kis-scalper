# kis-scalper v2 (realtime paper trading)

## Overview
This folder hosts the v2 realtime paper-trading framework driven by KIS OpenAPI ticks.

## Setup
- Python 3.12
- Install dependencies:
  - `pip install websockets pyyaml`

## Config
- Edit `v2/config/config.yaml`
- Add secrets to `v2/config/secrets.json` (APP_KEY, APP_SECRET, ACCOUNT_NO)

## Run
- Mock mode (default):
  - `python v2/main_realtime.py`
- Real KIS websocket (set `websocket.mock: false` in config)

## Structure (high level)
- `v2/kis_scalper_v2/`: connectivity, market data, execution, models, env, logging
- `v2/logs/`: transition and summary logs
- `v2/data/`: local data artifacts
