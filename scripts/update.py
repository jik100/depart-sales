"""日本百貨店協会の全国売上高(千円)を取得して data/sales.csv に追記する。
直近36か月で未取得の月をすべて埋める(初回は自動で過去分も取得)。"""
import re, csv, io, os, unicodedata, datetime, urllib.request
from urllib.parse import urljoin
from pypdf import PdfReader

CSV = "data/sales.csv"
BASE = "https://www.depart.or.jp/store_sale/"
UA = {"User-Agent": "Mozilla/5.0"}

def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=15) as r:
        return r.read()

def months(n=36):
    d = datetime.datetime.utcnow() + datetime.timedelta(hours=9)
    y, m = d.year, d.month - 1          # 発表されるのは前月分
    out = []
    for _ in range(n):
        if m == 0: y, m = y - 1, 12
        out.append(f"{y}{m:02d}"); m -= 1
    return out

def find_links(yms):
    links = {}
    for y in sorted({ym[:4] for ym in yms} | {str(int(ym[:4]) + 1) for ym in yms}):
        url = f"{BASE}{y}/"
        try: html = get(url).decode("latin-1")
        except Exception as e: print("skip", url, e); continue
        for href, ym in re.findall(r'href=["\']([^"\']*?(\d{6})zenkoku[^"\']*?\.pdf)', html, re.I):
            links[ym] = urljoin(url, href)
    return links

def parse(pdf_bytes):
    r = PdfReader(io.BytesIO(pdf_bytes))
    t = unicodedata.normalize("NFKC", "\n".join((p.extract_text() or "") for p in r.pages[:4]))
    t = re.sub(r"\s*,\s*", ",", t)
    m = re.search(r"全\s*国\s+(\d{1,3}(?:,\d{3}){2,})", t)
    if not m: raise ValueError("全国の売上高が見つからない")
    v = int(m.group(1).replace(",", ""))
    if not 10**8 <= v <= 2 * 10**9: raise ValueError(f"想定外の値 {v}")
    return v

rows = {}
if os.path.exists(CSV):
    for r in csv.DictReader(open(CSV, encoding="utf-8")):
        rows[r["month"]] = int(r["sales_kyen"])

wanted = [ym for ym in months() if f"{ym[:4]}-{ym[4:]}" not in rows]
links = find_links(wanted) if wanted else {}
for ym in wanted:
    url = links.get(ym, f"{BASE}files/{ym}zenkokupp.pdf")
    try:
        rows[f"{ym[:4]}-{ym[4:]}"] = parse(get(url))
        print("OK", ym, rows[f"{ym[:4]}-{ym[4:]}"])
    except Exception as e:
        print("未取得", ym, url, e)

with open(CSV, "w", encoding="utf-8", newline="") as f:
    f.write("month,sales_kyen\n")
    for k in sorted(rows): f.write(f"{k},{rows[k]}\n")
