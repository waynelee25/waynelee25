#!/usr/bin/env python3
"""
市場開盤日檢查工具
用法：
  python3 check_market_open.py tw    # 檢查台股今天是否開盤
  python3 check_market_open.py us    # 檢查美股今天是否開盤（台灣時間）

回傳：
  exit code 0 = 開盤（繼續執行）
  exit code 1 = 休市（跳過，不寄信）

時區說明：
  台股報告在台灣時間 07:00 執行 → 檢查台灣今天日期
  美股盤前報告在台灣時間 20:00 執行 → 美股尚未開盤，
  台灣 20:00 = 美東 08:00（同一天），直接用台灣今天日期比對美股假日
"""

import sys
from datetime import datetime
from zoneinfo import ZoneInfo

# ── 台灣時間今天日期（明確指定時區，不依賴系統時區） ─────────────────
TW_TODAY = datetime.now(ZoneInfo("Asia/Taipei")).date()

# ── 2026 台股休市日（TWSE 官方公告） ──────────────────────
TW_HOLIDAYS_2026 = {
    "2026-01-01",  # 中華民國開國紀念日
    "2026-02-15",  # 農曆除夕及春節
    "2026-02-16",  # 農曆除夕及春節
    "2026-02-17",  # 農曆除夕及春節
    "2026-02-18",  # 農曆除夕及春節
    "2026-02-19",  # 農曆除夕及春節
    "2026-02-20",  # 農曆除夕及春節（補假）
    "2026-02-27",  # 和平紀念日（補假）
    "2026-02-28",  # 和平紀念日
    "2026-04-03",  # 兒童節（補假）
    "2026-04-04",  # 兒童節
    "2026-04-05",  # 民族掃墓節
    "2026-04-06",  # 民族掃墓節（補假）
    "2026-05-01",  # 勞動節
    "2026-06-19",  # 端午節
    "2026-09-25",  # 中秋節
    "2026-09-28",  # 教師節
    "2026-10-09",  # 國慶日（補假）
    "2026-10-10",  # 國慶日
    "2026-10-25",  # 臺灣光復節
    "2026-10-26",  # 臺灣光復節（補假）
    "2026-12-25",  # 行憲紀念日
}

# ── 2026 美股（NYSE）休市日 ────────────────────────────────
US_HOLIDAYS_2026 = {
    "2026-01-01",  # New Year's Day
    "2026-01-19",  # MLK Day
    "2026-02-16",  # Presidents' Day
    "2026-04-03",  # Good Friday
    "2026-05-25",  # Memorial Day
    "2026-06-19",  # Juneteenth
    "2026-07-03",  # Independence Day (observed)
    "2026-09-07",  # Labor Day
    "2026-11-26",  # Thanksgiving
    "2026-12-25",  # Christmas
}

def check_tw():
    """檢查台股今天（台灣時間）是否開盤"""
    today_str = TW_TODAY.strftime("%Y-%m-%d")
    weekday = TW_TODAY.weekday()  # 0=週一, 6=週日

    if weekday >= 5:
        day_name = "週六" if weekday == 5 else "週日"
        print(f"🔴 台股休市：今天是{day_name}（{today_str}）")
        return False

    if today_str in TW_HOLIDAYS_2026:
        print(f"🔴 台股休市（國定假日）：{today_str}")
        return False

    print(f"✅ 台股開盤：{today_str}")
    return True

def check_us():
    """
    檢查美股今天是否開盤（台灣時間 20:00 執行）
    台灣 20:00 = 美東 08:00（同一天），距開盤 1.5 小時
    """
    today_str = TW_TODAY.strftime("%Y-%m-%d")
    weekday = TW_TODAY.weekday()

    if weekday >= 5:
        day_name = "週六" if weekday == 5 else "週日"
        print(f"🔴 美股休市：今天是{day_name}（{today_str}）")
        return False

    if today_str in US_HOLIDAYS_2026:
        print(f"🔴 美股休市（假日）：{today_str}")
        return False

    print(f"✅ 美股開盤日：{today_str}（台灣 20:00 = 美東 08:00，距開盤 1.5 小時）")
    return True

if __name__ == "__main__":
    market = sys.argv[1].lower() if len(sys.argv) > 1 else "us"

    if market == "tw":
        is_open = check_tw()
    elif market == "us":
        is_open = check_us()
    else:
        print(f"❌ 未知市場：{market}（請用 tw 或 us）")
        sys.exit(1)

    sys.exit(0 if is_open else 1)
