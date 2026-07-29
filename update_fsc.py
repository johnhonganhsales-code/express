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
    for fmt in ("%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(s.strip(), fmt).date()
        except:
            continue
    return None

def parse_pct(s):
    s = s.strip().replace("%","").replace(",",".")
    try:
        v = float(s)
        return v if 5 < v < 100 else None
    except:
        return None

lines = [l.strip() for l in soup.get_text("\n").split("\n") if l.strip()]

def get_fsc(carrier_keyword):
    """
    Sau khi tìm thấy section hãng:
    - Các dòng xen kẽ: ngày / % / ngày / % ...
    - Lấy cặp (ngày, %) đầu tiên có ngày <= hôm nay
    """
    start = None
    for i, line in enumerate(lines):
        if carrier_keyword.lower() in line.lower() and "surcharge" in line.lower():
            start = i
            break
    if start is None:
        print(f"Không tìm thấy section {carrier_keyword}")
        return None, None

    print(f"Section {carrier_keyword} bắt đầu dòng {start}: {lines[start]}")

    best_pct  = None
    best_date = None
    i = start + 1
    while i < len(lines) - 1:
        line = lines[i]
        # Kết thúc section khi gặp hãng khác
        if any(k.lower() in line.lower() and "surcharge" in line.lower()
               for k in ["DHL","FedEx","UPS"] if k.lower() != carrier_keyword.lower()):
            break

        d = parse_date(line)
        if d is not None:
            # Dòng tiếp theo là %
            pct = parse_pct(lines[i+1]) if i+1 < len(lines) else None
            print(f"  {d} -> {pct}%")
            if pct and d <= today:
                if best_date is None or d > best_date:
                    best_date = d
                    best_pct  = pct
        i += 1

    return best_pct, best_date.strftime("%d/%m/%Y") if best_date else None

dhl_pct,   dhl_date   = get_fsc("DHL")
fedex_pct, fedex_date = get_fsc("FedEx")
ups_pct,   ups_date   = get_fsc("UPS")

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
