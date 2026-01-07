import requests
import xml.etree.ElementTree as ET
import datetime
import csv
import json
import os
from io import StringIO

# =========================
# 基本設定
# =========================
OBS_CODE = "40191"  # 八幡観測所
UPDATED_DATE = datetime.date.today().strftime("%Y-%m-%d")

WARNING_FEED = "https://www.data.jma.go.jp/developer/xml/feed/extra.xml"

# =========================
# 注意報・警報（乾燥・強風）
# =========================
def get_warnings():
    r = requests.get(WARNING_FEED, timeout=15)
    r.encoding = "utf-8"
    root = ET.fromstring(r.text)

    dry = False
    wind = False

    ns = "{http://www.w3.org/2005/Atom}"

    for entry in root.findall(f"{ns}entry"):
        title = entry.find(f"{ns}title")
        if title is None or "福岡県" not in title.text:
            continue

        content = entry.find(f"{ns}content")
        if content is None or not content.text:
            continue

        xml = ET.fromstring(content.text)

        for item in xml.iter("Item"):
            area = item.find("Area/Name")
            kind = item.find("Kind/Name")

            if area is None or kind is None:
                continue

            if "北九州市" in area.text:
                if kind.text == "乾燥注意報":
                    dry = True
                if kind.text == "強風注意報":
                    wind = True

    return dry, wind

# =========================
# 降水量合計（前N日）
# =========================
def get_rain_sum(days):
    today = datetime.date.today()
    total = 0.0

    for i in range(days):
        day = today - datetime.timedelta(days=i + 1)
        ymd = day.strftime("%Y%m%d")

        url = f"https://www.data.jma.go.jp/obd/stats/data/mdrr/pre_rct/alltable/pre{ymd}.csv"
        r = requests.get(url, timeout=15)
        r.encoding = "shift_jis"

        reader = csv.reader(StringIO(r.text))
        for row in reader:
            if row and row[0] == OBS_CODE:
                try:
                    total += float(row[9])  # 日降水量
                except:
                    pass

    return round(total, 1)

# =========================
# 判定ロジック
# =========================
def judge(rain3, rain30, dry, wind):
    level = 0
    result = "該当なし"

    # 注意報レベル
    if rain3 <= 1 and (rain30 <= 30 or dry):
        level = 1
        result = "注意報レベルに該当"

    # 警報レベル
    if level == 1 and wind:
        level = 2
        result = "警報レベルに該当"

    return level, result

# =========================
# 履歴保存
# =========================
def save_history(row):
    exists = os.path.exists("history.csv")
    with open("history.csv", "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not exists:
            writer.writerow(["date", "level", "rain3", "rain30", "dry", "wind"])
        writer.writerow(row)

# =========================
# メイン処理
# =========================
def main():
    rain3 = get_rain_sum(3)
    rain30 = get_rain_sum(30)
    dry, wind = get_warnings()

    level, result = judge(rain3, rain30, dry, wind)

    data = {
        "updated": UPDATED_DATE,
        "level": level,
        "result": result,
        "rain3": rain3,
        "rain30": rain30,
        "dry": dry,
        "wind": wind
    }

    # WEB表示用JSON
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # 履歴保存
    save_history([
        UPDATED_DATE,
        level,
        rain3,
        rain30,
        int(dry),
        int(wind)
    ])

if __name__ == "__main__":
    main()
