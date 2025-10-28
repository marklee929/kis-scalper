import requests
from bs4 import BeautifulSoup

base_url = "https://www.dhlottery.co.kr/gameResult.do"
results = {}

for drw_no in range(1, 1195):
    payload = {
        "method": "byWin",
        "drwNo": drw_no
    }
    resp = requests.post(base_url, data=payload)
    soup = BeautifulSoup(resp.text, "html.parser")

    # <div class="num win"> 아래의 <span> 번호 추출
    win_div = soup.find("div", {"class": "num win"})
    if win_div:
        spans = win_div.find_all("span", {"class": lambda x: x and "ball_645" in x})
        numbers = [span.text.strip() for span in spans]
        results[drw_no] = numbers
        print(f"{drw_no}회: {numbers}")
    else:
        print(f"{drw_no}회: 당첨번호 없음")

# 필요하다면 파일로 저장
import json
with open("lotto_results.json", "w", encoding="utf-8") as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
