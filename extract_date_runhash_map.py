#!/usr/bin/env python3
import argparse
import csv
import re
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse, parse_qs

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


def daterange(start_iso: str, end_iso: str):
    start = datetime.strptime(start_iso, "%Y-%m-%d")
    end = datetime.strptime(end_iso, "%Y-%m-%d")
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def get_qparam_from_url(url: str):
    qs = parse_qs(urlparse(url).query)
    vals = qs.get("qParam", [])
    return vals[0] if vals else ""


def run_extract(start_iso: str, end_iso: str, start_url: str, out_csv: Path, sample: int = 0, headless: bool = True):
    rows = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()

        page.goto(start_url, wait_until="domcontentloaded", timeout=60000)

        # Dismiss landing modal if shown.
        enter_btn = page.get_by_role("button", name=re.compile(r"Enter Website|เข้าสู่ระบบ TTS", re.I))
        if enter_btn.count() > 0:
            try:
                enter_btn.first.click(timeout=3000)
            except Exception:
                pass

        # Ensure Archive mode and core controls are visible.
        archive_toggle = page.get_by_text("Archive", exact=True)
        if archive_toggle.count() > 0:
            try:
                archive_toggle.first.click(timeout=3000)
            except Exception:
                pass

        date_input = page.get_by_role("textbox", name=re.compile(r"Search by date", re.I)).first
        date_input.wait_for(timeout=30000)

        search_buttons = page.locator('button:has-text("Search")')
        if search_buttons.count() == 0:
            raise RuntimeError("Search button not found")
        search_btn = search_buttons.last

        all_dates = list(daterange(start_iso, end_iso))
        if sample and sample > 0:
            all_dates = all_dates[:sample]

        total = len(all_dates)
        for idx, d in enumerate(all_dates, start=1):
            date_ddmmyyyy = d.strftime("%d/%m/%Y")
            date_iso = d.strftime("%Y-%m-%d")

            ok = False
            runhash = ""
            for attempt in range(1, 4):
                try:
                    date_input.click()
                    date_input.fill("")
                    date_input.type(date_ddmmyyyy)

                    search_btn.click()

                    # URL usually updates quickly with new qParam.
                    page.wait_for_timeout(900)
                    runhash = get_qparam_from_url(page.url)

                    # If URL didn't update yet, wait one more beat.
                    if not runhash:
                        page.wait_for_timeout(1200)
                        runhash = get_qparam_from_url(page.url)

                    if runhash:
                        rows.append({"date": date_iso, "runhash": runhash})
                        ok = True
                        print(f"[{idx}/{total}] {date_iso} -> {runhash}")
                        break
                except PlaywrightTimeoutError:
                    pass
                except Exception:
                    pass

                page.wait_for_timeout(600)

            if not ok:
                rows.append({"date": date_iso, "runhash": ""})
                print(f"[{idx}/{total}] {date_iso} -> MISSING")

        context.close()
        browser.close()

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "runhash"])
        writer.writeheader()
        writer.writerows(rows)

    missing = sum(1 for r in rows if not r["runhash"])
    print(f"Saved {len(rows)} rows to {out_csv}")
    print(f"Missing runhash rows: {missing}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", default="2024-06-01")
    parser.add_argument("--end", default="2026-05-08")
    parser.add_argument("--url", required=True, help="Archive URL containing qType=21&qParam=... for target train")
    parser.add_argument("--output", default="/Users/Taspol/Documents/sideProject/train_scrape/new/date_runhash_map.csv")
    parser.add_argument("--sample", type=int, default=0)
    parser.add_argument("--headed", action="store_true")
    args = parser.parse_args()

    run_extract(
        start_iso=args.start,
        end_iso=args.end,
        start_url=args.url,
        out_csv=Path(args.output),
        sample=args.sample,
        headless=not args.headed,
    )


if __name__ == "__main__":
    main()
