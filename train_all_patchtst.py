import os
import subprocess
from datetime import date

# 날짜 자동 설정
today = date.today().isoformat().replace("-", "")
data_root = f"./crawling/{today}"
csv_files = [f for f in os.listdir(data_root) if f.endswith("_5min.csv")]

print(f"🧠 총 {len(csv_files)}개 종목 학습 시작...\n")

for file in csv_files:
    code_id = file.replace("_5min.csv", "")
    model_id = f"{code_id}_5min"

    print(f"🚀 학습 시작: {file} → 모델 ID: {model_id}")

    # ✅ run_longExp.py 파일 전체 경로
    script_path = os.path.abspath("PatchTST/PatchTST_supervised/run_longExp.py")

    cmd = [
        "python", script_path,
        "--is_training", "1",
        "--root_path", data_root,
        "--data_path", file,
        "--model_id", model_id,
        "--model", "PatchTST",
        "--data", "custom",
        "--features", "M",
        "--seq_len", "60",
        "--label_len", "30",
        "--pred_len", "12",
        "--e_layers", "2",
        "--d_model", "64",
        "--n_heads", "4",
        "--patch_len", "24",
        "--stride", "12",
        "--des", "batch-scalping",
        "--itr", "1",
        "--num_workers", "0",  # ← 멀티 프로세스 안 씀
    ]

    # ✅ PYTHONPATH 환경 변수에 PatchTST_supervised 상위 폴더 추가
    env = os.environ.copy()
    env["PYTHONPATH"] = os.path.abspath("PatchTST")

    subprocess.run(cmd, env=env)
    print(f"✅ 완료: {file}\n")

print("🎉 전체 학습 완료!")
