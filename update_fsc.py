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

def get_latest_fsc(carrier_keyword):
    """
    Tìm table chứa đúng tên hãng trong <th> hoặc <td> header,
    trả về (pct float, date string) của dòng dữ liệu đầu tiên.
    """
    tables = soup.find_all("table")
    for table in tables:
        # Kiểm tra header của bảng có chứa tên hãng không
        headers_text = " ".join(th.get_text(strip=True) for th in table.find_all(["th","td"])[:3])
        if carrier_keyword.lower() not in headers_text.lower():
            continue
        # Lấy tất cả rows, bỏ qua header
        rows = table.find_all("tr")
        for row in rows:
            cols = [td.get_text(strip=True) for td in row.find_all("td")]
            if len(cols) < 2:
                continue
            date_str = cols[0].strip()
            pct_str  = cols[1].strip().replace("%", "").replace(",", ".")
            try:
                pct = float(pct_str)
                if pct > 100:   # sanity check — FSC không thể > 100%
                    continue
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

# Ghi số thực (vd 38.25) — sheet tự format thành %
ws.update("B6", [[dhl_pct / 100]])
ws.update("B7", [[ups_pct / 100]])
ws.update("B8", [[fedex_pct / 100]])

# Ghi ngày hiệu lực cột E
ws.update("E6", [[dhl_date]])
ws.update("E7", [[ups_date]])
ws.update("E8", [[fedex_date]])

print(f"✅ Cập nhật thành công lúc {datetime.now().strftime('%d/%m/%Y %H:%M')}")
