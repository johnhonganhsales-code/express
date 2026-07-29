import requests
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials
import json, os
from datetime import datetime

# ── 1. Crawl FSC ──────────────────────────────────────────
url = "https://www.thepostalconnect.com/rw/fuel-surcharge.asp"
headers = {"User-Agent": "Mozilla/5.0"}
res = requests.get(url, headers=headers, timeout=15)
res.raise_for_status()
soup = BeautifulSoup(res.text, "html.parser")

# Debug: in toàn bộ text để kiểm tra
full_text = soup.get_text()
print("=== PAGE TEXT (500 chars) ===")
print(full_text[:2000])
print("=== END ===")

def get_latest_fsc(carrier_keyword):
    # Tìm tất cả text chứa keyword, lấy % gần nhất
    text = soup.get_text("\n")
    lines = text.split("\n")
    found_carrier = False
    for line in lines:
        line = line.strip()
        if carrier_keyword.lower() in line.lower() and "surcharge" in line.lower():
            found_carrier = True
            continue
        if found_carrier and "%" in line:
            # Lấy dòng đầu tiên có ngày và %
            parts = line.split()
            for part in parts:
                pct_str = part.replace("%","").replace(",",".").strip()
                try:
                    pct = float(pct_str)
                    if 10 < pct < 100:
                        return pct, ""
                except:
                    continue
    return None, None

dhl_pct,   dhl_date   = get_latest_fsc("DHL")
fedex_pct, fedex_date = get_latest_fsc("FedEx")
ups_pct,   ups_date   = get_latest_fsc("UPS")

print(f"DHL:   {dhl_pct}%")
print(f"FedEx: {fedex_pct}%")
print(f"UPS:   {ups_pct}%")

if None in [dhl_pct, fedex_pct, ups_pct]:
    raise ValueError(f"Thiếu dữ liệu: DHL={dhl_pct}, FedEx={fedex_pct}, UPS={ups_pct}")

# ── 2. Ghi vào Google Sheet ───────────────────────────────
creds_json = json.loads(os.environ["GOOGLE_CREDENTIALS"])
creds = Credentials.from_service_account_info(
    creds_json,
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
gc = gspread.authorize(creds)

SHEET_ID = os.environ["SHEET_ID"]
sh = gc.open_by_key(SHEET_ID)
ws = sh.worksheet("Settings")

ws.update("B6", [[dhl_pct / 100]])
ws.update("B7", [[ups_pct / 100]])
ws.update("B8", [[fedex_pct / 100]])

print(f"✅ Cập nhật thành công lúc {datetime.now().strftime('%d/%m/%Y %H:%M')}")
