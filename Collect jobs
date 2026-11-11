#!/usr/bin/env python3
"""
collect_jobs.py - ดึงประกาศงานจากหลายแหล่ง แปลงเป็นรูปแบบเดียวกัน ตัดซ้ำ แล้วเขียน jobs.json

ใช้เฉพาะ standard library (ไม่ต้อง pip install)
วิธีรัน:   python3 collect_jobs.py --out jobs.json
ตั้งเวลา:  cron เช่น  0 6 * * *  (วันละครั้ง) อย่าถี่กว่านี้ เพราะ API ฟรีขอให้ใช้เบา ๆ และโควตา Adzuna จำกัด
           (แต่ละรอบเขียนทับ jobs.json ทั้งไฟล์ จึงรันทุกแหล่งในคำสั่งเดียว)

เพิ่มแหล่งใหม่: เขียนฟังก์ชัน from_xxx() ที่ yield make_job(...) แล้วเพิ่มเข้า SOURCES
"""
import argparse
import hashlib
import html
import json
import os
import re
import sys
import time
from functools import partial
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

# ใส่อีเมลหรือเว็บของคุณ เพื่อให้เจ้าของ API ติดต่อได้ถ้ามีปัญหา
USER_AGENT = "WorldwideJobsBot/0.1 (+mailto:kaninrasameebaramee@email.com)"
SNIPPET_LEN = 200  # เก็บแค่ข้อความสั้น ๆ ไม่คัดลอกทั้งประกาศ

# ---------------------------------------------------------------- helpers

def fetch_json(url, timeout=20):
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(req, timeout=timeout) as resp:
        return json.load(resp)


def strip_html(text):
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", html.unescape(text)).strip()


def snippet(text):
    text = strip_html(text)
    return text if len(text) <= SNIPPET_LEN else text[: SNIPPET_LEN - 1].rstrip() + "…"


def to_date(value):
    """รับ unix timestamp หรือสตริง ISO แล้วคืนเป็น YYYY-MM-DD (หรือ None)"""
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc).strftime("%Y-%m-%d")
    return str(value)[:10]


REGION_KEYWORDS = {
    "ยุโรป": ["europe", "emea", "uk", "united kingdom", "germany", "france", "spain", "italy",
              "netherlands", "poland", "portugal", "sweden", "norway", "denmark", "finland",
              "ireland", "austria", "switzerland", "belgium", "berlin", "london", "paris",
              "amsterdam", "munich", "hamburg", "vienna", "zurich", "madrid", "lisbon"],
    "เอเชีย": ["asia", "apac", "singapore", "thailand", "bangkok", "india", "japan", "tokyo",
               "korea", "china", "hong kong", "malaysia", "indonesia", "vietnam", "philippines"],
    "อเมริกาเหนือ": ["usa", "united states", "us only", "canada", "north america", "new york",
                     "san francisco", "toronto", "vancouver", "austin", "seattle", "americas"],
    "อเมริกาใต้และกลาง": ["latam", "latin america", "brazil", "mexico", "argentina", "colombia",
                          "chile", "peru"],
    "แอฟริกา": ["africa", "nigeria", "kenya", "south africa", "egypt", "ghana"],
    "โอเชียเนีย": ["australia", "new zealand", "sydney", "melbourne", "oceania"],
}
WORLDWIDE = ["worldwide", "anywhere", "global", "world wide", "any location"]


def infer_region(location):
    loc = (location or "").lower()
    if not loc or any(w in loc for w in WORLDWIDE):
        return "ทั่วโลก"
    for region, words in REGION_KEYWORDS.items():
        if any(re.search(r"\b" + re.escape(w) + r"\b", loc) for w in words):
            return region
    return "อื่น ๆ"


def make_job(*, title, company, location, work_type, employment, skills, posted_at,
             url, source_name, source_url, description, region=None):
    return {
        "title": strip_html(title),
        "company": strip_html(company),
        "location": strip_html(location) or "ทั่วโลก",
        "region": region or infer_region(location),
        "work_type": work_type,          # Remote / Hybrid / Onsite
        "employment": employment,        # full_time, contract ...
        "skills": [x for x in (strip_html(s) for s in (skills or [])) if x][:6],
        "posted_at": to_date(posted_at),
        "url": url,                      # หน้าต้นฉบับสำหรับสมัคร
        "source_name": source_name,
        "source_url": source_url,
        "snippet": snippet(description),
    }

# ---------------------------------------------------------------- sources

def from_remotive():
    data = fetch_json("https://remotive.com/api/remote-jobs")
    for j in data.get("jobs", []):
        yield make_job(
            title=j.get("title"), company=j.get("company_name"),
            location=j.get("candidate_required_location") or "Worldwide",
            work_type="Remote", employment=j.get("job_type") or "",
            skills=j.get("tags"), posted_at=j.get("publication_date"),
            url=j.get("url"), source_name="Remotive", source_url="https://remotive.com",
            description=j.get("description"),
        )


def from_arbeitnow(max_pages=3):
    url = "https://www.arbeitnow.com/api/job-board-api"
    for _ in range(max_pages):
        data = fetch_json(url)
        for j in data.get("data", []):
            job_types = j.get("job_types") or []
            yield make_job(
                title=j.get("title"), company=j.get("company_name"),
                location=j.get("location"),
                work_type="Remote" if j.get("remote") else "Onsite",
                employment=job_types[0] if job_types else "",
                skills=j.get("tags"), posted_at=j.get("created_at"),
                url=j.get("url"), source_name="Arbeitnow",
                source_url="https://www.arbeitnow.com", description=j.get("description"),
            )
        url = (data.get("links") or {}).get("next")
        if not url:
            break
        time.sleep(1)  # เว้นช่วงระหว่างหน้า


# Adzuna: ต้องสมัครขอคีย์ฟรีที่ developer.adzuna.com แล้วตั้ง environment variable
#   export ADZUNA_APP_ID=xxxx ADZUNA_APP_KEY=yyyy
# ประเทศที่รองรับอาจเปลี่ยนได้ ตรวจรายการล่าสุดที่ developer.adzuna.com ก่อนเพิ่มประเทศ
ADZUNA_COUNTRIES = {  # รหัสประเทศ: (ชื่อไทย, ภูมิภาค)
    "gb": ("สหราชอาณาจักร", "ยุโรป"), "de": ("เยอรมนี", "ยุโรป"), "fr": ("ฝรั่งเศส", "ยุโรป"),
    "nl": ("เนเธอร์แลนด์", "ยุโรป"), "es": ("สเปน", "ยุโรป"), "it": ("อิตาลี", "ยุโรป"),
    "pl": ("โปแลนด์", "ยุโรป"), "at": ("ออสเตรีย", "ยุโรป"), "be": ("เบลเยียม", "ยุโรป"),
    "ch": ("สวิตเซอร์แลนด์", "ยุโรป"), "us": ("สหรัฐอเมริกา", "อเมริกาเหนือ"),
    "ca": ("แคนาดา", "อเมริกาเหนือ"), "mx": ("เม็กซิโก", "อเมริกาใต้และกลาง"),
    "br": ("บราซิล", "อเมริกาใต้และกลาง"), "au": ("ออสเตรเลีย", "โอเชียเนีย"),
    "nz": ("นิวซีแลนด์", "โอเชียเนีย"), "sg": ("สิงคโปร์", "เอเชีย"), "in": ("อินเดีย", "เอเชีย"),
    "za": ("แอฟริกาใต้", "แอฟริกา"),
}
# ค่าเริ่มต้น 8 ประเทศ = 8 calls ต่อรอบ (ฟรีทิเออร์ราว 1,000 calls/เดือน จึงควรรัน Adzuna วันละครั้ง)
ADZUNA_DEFAULT = ["gb", "us", "de", "ca", "au", "sg", "in", "za"]


def work_type_from_text(text):
    t = (text or "").lower()
    if "remote" in t:
        return "Remote"
    if "hybrid" in t:
        return "Hybrid"
    return "ไม่ระบุ"  # Adzuna ไม่มีฟิลด์นี้ จึงไม่เดาว่าเป็น Onsite


def from_adzuna(countries=ADZUNA_DEFAULT, pages=1):
    app_id, app_key = os.environ.get("ADZUNA_APP_ID"), os.environ.get("ADZUNA_APP_KEY")
    if not app_id or not app_key:
        raise RuntimeError("ไม่พบ ADZUNA_APP_ID / ADZUNA_APP_KEY ใน environment")
    first = True
    for cc in countries:
        name_th, region = ADZUNA_COUNTRIES[cc]
        for page in range(1, pages + 1):
            if not first:
                time.sleep(1)
            first = False
            qs = urlencode({"app_id": app_id, "app_key": app_key,
                            "results_per_page": 50, "content-type": "application/json"})
            data = fetch_json(f"https://api.adzuna.com/v1/api/jobs/{cc}/search/{page}?{qs}")
            for j in data.get("results", []):
                place = ((j.get("location") or {}).get("display_name") or "").strip()
                title = j.get("title") or ""
                desc = j.get("description") or ""
                yield make_job(
                    title=title, company=(j.get("company") or {}).get("display_name"),
                    location=f"{place}, {name_th}" if place else name_th, region=region,
                    work_type=work_type_from_text(title + " " + desc),
                    employment=j.get("contract_time") or "",
                    skills=[(j.get("category") or {}).get("label") or ""],
                    posted_at=j.get("created"), url=j.get("redirect_url"),
                    source_name="Adzuna", source_url="https://www.adzuna.com", description=desc,
                )


SOURCES = {"remotive": from_remotive, "arbeitnow": from_arbeitnow, "adzuna": from_adzuna}

# ---------------------------------------------------------------- pipeline

def is_valid(job):
    url = job.get("url") or ""
    # ต้องมีลิงก์ต้นฉบับแบบ http(s) เท่านั้น (กัน javascript: และรายการที่ไม่มีที่มา)
    return bool(job["title"] and job["company"]) and url.startswith(("http://", "https://"))


def dedupe_key(job):
    raw = "|".join(re.sub(r"\W+", "", job[k].lower()) for k in ("title", "company", "location"))
    return hashlib.sha1(raw.encode()).hexdigest()


def collect(selected, sources=SOURCES, log=print):
    jobs, seen, per_source, failed = [], set(), {}, []
    fetched_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    for name in selected:
        try:
            count = 0
            for job in sources[name]():
                if not is_valid(job):
                    continue
                key = dedupe_key(job)
                if key in seen:
                    continue
                seen.add(key)
                job["fetched_at"] = fetched_at
                jobs.append(job)
                count += 1
            per_source[name] = count
            log(f"[ok]   {name}: {count} รายการ")
        except Exception as exc:  # แหล่งหนึ่งพัง ไม่ควรทำให้ทั้งระบบพัง
            failed.append(name)
            log(f"[fail] {name}: {exc}")
    jobs.sort(key=lambda j: j["posted_at"] or "", reverse=True)
    return jobs, per_source, failed, fetched_at


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default="jobs.json")
    has_adzuna = bool(os.environ.get("ADZUNA_APP_ID") and os.environ.get("ADZUNA_APP_KEY"))
    ap.add_argument("--sources", nargs="+", choices=list(SOURCES),
                    default=[s for s in SOURCES if s != "adzuna" or has_adzuna],
                    help="ค่าเริ่มต้นรวม adzuna เฉพาะเมื่อตั้งคีย์ไว้แล้ว")
    ap.add_argument("--adzuna-countries", nargs="+", default=ADZUNA_DEFAULT, choices=list(ADZUNA_COUNTRIES))
    ap.add_argument("--adzuna-pages", type=int, default=1, help="จำนวนหน้า (50 รายการ/หน้า) ต่อประเทศ")
    ap.add_argument("--limit", type=int, default=500, help="จำนวนประกาศสูงสุดที่เก็บ")
    args = ap.parse_args()

    log = lambda m: print(m, file=sys.stderr)
    sources = dict(SOURCES)
    sources["adzuna"] = partial(from_adzuna, args.adzuna_countries, args.adzuna_pages)
    jobs, per_source, failed, fetched_at = collect(args.sources, sources=sources, log=log)
    if not jobs:
        log("ไม่ได้ข้อมูลเลย จึงไม่เขียนทับไฟล์เดิม")
        sys.exit(1)

    jobs = jobs[: args.limit]
    payload = {"generated_at": fetched_at, "count": len(jobs), "sources": per_source, "jobs": jobs}
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=1)
    log(f"เขียน {len(jobs)} รายการลง {args.out}")
    if failed:
        sys.exit(2)  # สำเร็จบางส่วน


if __name__ == "__main__":
    main()
