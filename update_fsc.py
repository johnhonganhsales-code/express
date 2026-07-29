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

# In 50 dòng đầu của text để xem cấu trúc
lines = [l.strip() for l in soup.get_text("\n").split("\n") if l.strip()]
print("=== 80 DÒNG ĐẦU ===")
for i, l in enumerate(lines[:80]):
    print(f"{i:3}: {l}")
print("=== HẾT ===")
