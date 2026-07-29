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

today = datetime.today().date()

def parse_date(s):
    """Parse dd/mm/yyyy hoặc yyyy/mm/dd"""
    s = s.strip()
    for fmt in ("%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except:
            continue
    return None

def get_latest_fsc(carrier_keyword):
    """
    Tìm bảng đúng hãng, lấy dòng mới nhất có ngày hiệu lực <= hôm nay
    """
    tables = soup.find_all("table")
    for table in tables:
        header_text = " ".join(
            cell.get_text(strip=True)
            for cell in table.find_all(["th", "td"])[:5]
        )
        if carrier_keyword.lower() not in header_text.lower():
            continue

        rows = table.find_all("tr")
        best_pct  = None
        best_date = None

        for row in rows:
            cols = [td.get_text(strip=True) for td in row.find_all("td")]
            if len(cols) < 2:
                continue
            eff_date = parse_date(cols[0])
            if eff_date is None:
                continue
            pct_str = cols[1].replace("%", "").replace(",", ".").strip()
            try:
                pct = float(pct_str)
            except:
                continue
            if not (5 < pct < 100):
                continue
            # Chỉ lấy ngày <= hôm nay, ưu tiên ngày gần nhất
            if eff_date <= today:
                if best_date is None or eff_date > best_date:
                    best_date = eff_date
                    best_pct  = pct

        if best_pct is not None:
            return best_pct, best_date.strftime("%d/%m/%Y")

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

ws.update("B6", [[dhl_pct / 100]])
ws.update("B7", [[ups_pct / 100]])
ws.update("B8", [[fedex_pct / 100]])

ws.update("E6", [[dhl_date]])
ws.update("E7", [[ups_date]])
ws.update("E8", [[fedex_date]])

print(f"✅ Cập nhật thành công lúc {datetime.now().strftime('%d/%m/%Y %H:%M')}")
