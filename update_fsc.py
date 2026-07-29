import requests
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials
import json, os, re
from datetime import datetime

# ── 1. Crawl FSC từ thepostalconnect.com ──────────────────
url = "https://www.thepostalconnect.com/rw/fuel-surcharge.asp"
headers = {"User-Agent": "Mozilla/5.0"}
res = requests.get(url, headers=headers, timeout=15)
res.raise_for_status()
soup = BeautifulSoup(res.text, "html.parser")

def get_latest_fsc(carrier_keyword):
    """Tìm bảng chứa tên hãng, trả về (pct, effective_date) của dòng mới nhất"""
    tables = soup.find_all("table")
    for table in tables:
        header_text = table.get_text(" ", strip=True).lower()
        if carrier_keyword.lower() not in header_text:
            continue
        rows = table.find_all("tr")
        for row in rows:
            cols = [td.get_text(strip=True) for td in row.find_all("td")]
            if len(cols) < 2:
                continue
            date_str = cols[0].strip()
            pct_str  = cols[1].strip().replace("%", "")
            try:
                pct = float(pct_str)
                # Parse date dd/mm/yyyy -> dd/mm/yyyy (giữ nguyên để ghi vào sheet)
                return pct, date_str
            except ValueError:
                continue
    return None, None

dhl_pct,   dhl_date   = get_latest_fsc("DHL")
fedex_pct, fedex_date = get_latest_fsc("FedEx")
ups_pct,   ups_date   = get_latest_fsc("UPS")

print(f"DHL:   {dhl_pct}%  ({dhl_date})")
print(f"FedEx: {fedex_pct}%  ({fedex_date})")
print(f"UPS:   {ups_pct}%  ({ups_date})")

if None in [dhl_pct, fedex_pct, ups_pct]:
    raise ValueError("Không crawl được đủ 3 hãng — kiểm tra lại HTML trang web")

# ── 2. Ghi vào Google Sheet ────────────────────────────────
creds_json = json.loads(os.environ["GOOGLE_CREDENTIALS"])
creds = Credentials.from_service_account_info(
    creds_json,
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
gc = gspread.authorize(creds)

SHEET_ID = os.environ["SHEET_ID"]
sh = gc.open_by_key(SHEET_ID)
ws = sh.worksheet("Settings")   # tên tab trong spreadsheet

# Ghi Fuel (%) vào cột B — lưu số thập phân (vd 38.25)
ws.update("B6", [[dhl_pct]])
ws.update("B7", [[ups_pct]])
ws.update("B8", [[fedex_pct]])

# Ghi ngày hiệu lực vào cột E
ws.update("E6", [[dhl_date]])
ws.update("E7", [[ups_date]])
ws.update("E8", [[fedex_date]])

print(f"✅ Đã cập nhật sheet lúc {datetime.now().strftime('%d/%m/%Y %H:%M')}")
