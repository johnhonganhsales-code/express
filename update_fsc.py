import requests
from bs4 import BeautifulSoup
import gspread
from google.oauth2.service_account import Credentials
import json, os, re
from datetime import datetime

url = "https://www.thepostalconnect.com/rw/fuel-surcharge.asp"
headers = {"User-Agent": "Mozilla/5.0"}
res = requests.get(url, headers=headers, timeout=15)
res.raise_for_status()
soup = BeautifulSoup(res.text, "html.parser")

today = datetime.today().date()
print(f"Hôm nay: {today}")

def parse_date(s):
    s = s.strip()
    for fmt in ("%d/%m/%Y", "%Y/%m/%d", "%d/%m/%y"):
        try:
            return datetime.strptime(s, fmt).date()
        except:
            continue
    return None

def get_fsc_from_text(full_text, carrier_keyword):
    """
    Tìm section của hãng trong text, quét từng dòng có ngày + %,
    lấy dòng mới nhất có ngày <= hôm nay
    """
    lines = full_text.split("\n")
    in_section = False
    best_pct = None
    best_date = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Phát hiện bắt đầu section hãng
        if carrier_keyword.lower() in line.lower() and ("surcharge" in line.lower() or "fuel" in line.lower()):
            in_section = True
            print(f">>> Tìm thấy section: {line}")
            continue

        # Kết thúc section khi gặp hãng khác
        if in_section:
            other = [k for k in ["DHL","FedEx","UPS"] if k.lower() != carrier_keyword.lower()]
            if any(k.lower() in line.lower() and "surcharge" in line.lower() for k in other):
                break

        if not in_section:
            continue

        # Tìm dòng có ngày
        date_match = re.search(r'(\d{2}/\d{2}/\d{4}|\d{4}/\d{2}/\d{2})', line)
        pct_match  = re.search(r'(\d{1,3}[.,]\d{1,2})%', line)

        if date_match and pct_match:
            eff_date = parse_date(date_match.group(1))
            pct_str  = pct_match.group(1).replace(",",".")
            try:
                pct = float(pct_str)
            except:
                continue
            print(f"  Dòng: {line} -> date={eff_date}, pct={pct}%")
            if eff_date and eff_date <= today:
                if best_date is None or eff_date > best_date:
                    best_date = eff_date
                    best_pct  = pct

    return best_pct, best_date.strftime("%d/%m/%Y") if best_date else None

full_text = soup.get_text("\n")

dhl_pct,   dhl_date   = get_fsc_from_text(full_text, "DHL")
fedex_pct, fedex_date = get_fsc_from_text(full_text, "FedEx")
ups_pct,   ups_date   = get_fsc_from_text(full_text, "UPS")

print(f"\nKết quả:")
print(f"DHL:   {dhl_pct}%  ({dhl_date})")
print(f"FedEx: {fedex_pct}%  ({fedex_date})")
print(f"UPS:   {ups_pct}%  ({ups_date})")

if None in [dhl_pct, fedex_pct, ups_pct]:
    raise ValueError(f"Thiếu dữ liệu: DHL={dhl_pct}, FedEx={fedex_pct}, UPS={ups_pct}")

# ── Ghi vào Google Sheet ──────────────────────────────────
creds_json = json.loads(os.environ["GOOGLE_CREDENTIALS"])
creds = Credentials.from_service_account_info(
    creds_json,
    scopes=["https://www.googleapis.com/auth/spreadsheets"]
)
gc = gspread.authorize(creds)

SHEET_ID = os.environ["SHEET_ID"]
sh = gc.open_by_key(SHEET_ID)
ws = sh.worksheet("Settings")

ws.update(range_name="B6", values=[[dhl_pct / 100]])
ws.update(range_name="B7", values=[[ups_pct / 100]])
ws.update(range_name="B8", values=[[fedex_pct / 100]])
ws.update(range_name="E6", values=[[dhl_date]])
ws.update(range_name="E7", values=[[ups_date]])
ws.update(range_name="E8", values=[[fedex_date]])

print(f"✅ Xong lúc {datetime.now().strftime('%d/%m/%Y %H:%M')}")
