import os
import re
import requests
import pdfplumber
import pandas as pd

from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime

BASE = "https://www.kilimo.go.tz"
START_URL = "https://www.kilimo.go.tz/publications/market-bulletin"

OUT_DIR = "kilimo_pdfs"
os.makedirs(OUT_DIR, exist_ok=True)

MONTHS = {
    "january": 1,
    "januari": 1,
    "february": 2,
    "februari": 2,
    "march": 3,
    "machi": 3,
    "april": 4,
    "aprili": 4,
    "may": 5,
    "mei": 5,
    "june": 6,
    "juni": 6,
    "july": 7,
    "julai": 7,
    "august": 8,
    "agosti": 8,
    "september": 9,
    "septemba": 9,
    "october": 10,
    "oktoba": 10,
    "november": 11,
    "novemba": 11,
    "december": 12,
    "desemba": 12,
}


def price(x):
    if not x:
        return None

    x = str(x).strip()

    # remove arrows/symbols
    x = x.replace("▲", "")
    x = x.replace("▼", "")
    x = x.replace("►", "")

    # remove spaces and commas
    x = x.replace(" ", "")
    x = x.replace(",", "")

    if x in ["", "-"]:
        return None

    # keep only digits
    x = re.sub(r"[^\d]", "", x)

    if not x:
        return None

    return int(x)


def get_average_date(text):
    text = text.replace("–", "-")
    text = re.sub(r"(\d+)(st|nd|rd|th)", r"\1", text, flags=re.I)

    # Example:
    # 04 - 08 May, 2026
    # 04 - 08 Mei, 2026
    m = re.search(
        r"(\d{1,2})\s*-\s*(\d{1,2})\s+([A-Za-zÀ-ÿ]+),?\s*(20\d{2})",
        text,
        re.I,
    )

    if not m:
        return None

    d1, d2, month_name, year = m.groups()

    month = MONTHS.get(month_name.lower())

    if not month:
        return None

    start = datetime(int(year), month, int(d1))
    end = datetime(int(year), month, int(d2))

    avg = start + (end - start) / 2

    return avg.date().isoformat()


def get_pdf_links(max_pages=30):
    pdfs = set()

    for page in range(1, max_pages + 1):

        if page == 1:
            url = START_URL
        else:
            url = f"{START_URL}?page={page}"

        print("Checking:", url)

        r = requests.get(url, timeout=30)

        if r.status_code != 200:
            break

        soup = BeautifulSoup(r.text, "html.parser")

        found = 0

        for a in soup.find_all("a", href=True):

            href = urljoin(BASE, a["href"])

            if href.lower().endswith(".pdf") and "uploads/documents" in href:
                pdfs.add(href)
                found += 1

        if found == 0:
            break

    return sorted(pdfs)


def download_pdf(url):
    filename = url.split("/")[-1].replace("%20", " ")

    path = os.path.join(OUT_DIR, filename)

    if not os.path.exists(path):

        print("Downloading:", filename)

        r = requests.get(url, timeout=120)
        r.raise_for_status()

        with open(path, "wb") as f:
            f.write(r.content)

    return path, filename


def extract_prices(pdf_path, pdf_name, url):

    rows = []

    with pdfplumber.open(pdf_path) as pdf:

        full_text = ""

        for p in pdf.pages:
            full_text += "\n" + (p.extract_text() or "")

        avg_date = get_average_date(full_text)

        if not avg_date:
            print("Could not get date:", pdf_name)
            return rows

        for page_number, page in enumerate(pdf.pages, start=1):

            try:
                tables = page.extract_tables()

                for table in tables:

                    for row in table:

                        if not row:
                            continue

                        row = [
                            str(c).replace("\n", " ").strip() if c else ""
                            for c in row
                        ]

                        # Skip bad rows
                        if len(row) < 5:
                            continue

                        region = row[0].strip()
                        week = row[1].strip().lower()

                        # only current rows
                        if week not in ["current", "wiki hii", "sasa"]:
                            continue

                        # expected:
                        # Region | Week | Maize | Rice | Beans | ...

                        rice_value = price(row[3])
                        beans_value = price(row[4])

                        if rice_value is not None:
                            rows.append({
                                "Region": region,
                                "date": avg_date,
                                "crop": "Rice",
                                "price_tzs_per_kg": rice_value,
                                "source_pdf": pdf_name,
                                "source_url": url,
                            })

                        if beans_value is not None:
                            rows.append({
                                "Region": region,
                                "date": avg_date,
                                "crop": "Beans",
                                "price_tzs_per_kg": beans_value,
                                "source_pdf": pdf_name,
                                "source_url": url,
                            })

            except Exception as e:
                print(f"Table extraction failed on page {page_number}: {e}")

    return rows


def main():

    all_rows = []

    pdf_links = get_pdf_links()

    print(f"\nFound {len(pdf_links)} PDFs\n")

    for url in pdf_links:

        try:
            pdf_path, pdf_name = download_pdf(url)

            rows = extract_prices(pdf_path, pdf_name, url)

            all_rows.extend(rows)

            print("OK:", pdf_name)

        except Exception as e:

            print("FAILED:", url, e)

    df = pd.DataFrame(all_rows)

    if df.empty:
        print("No data extracted.")
        return

    # clean
    df = df.dropna(subset=["Region", "date", "price_tzs_per_kg"])

    # remove weird rows
    df = df[df["Region"].str.len() > 1]

    # sort
    df = df.sort_values(["date", "Region", "crop"])

    # LONG FORMAT
    df.to_csv("kilimo_rice_beans_long.csv", index=False)

    # WIDE FORMAT
    wide = (
        df.pivot_table(
            index=["Region", "date"],
            columns="crop",
            values="price_tzs_per_kg",
            aggfunc="first",
        )
        .reset_index()
    )

    wide.to_csv("kilimo_rice_beans_wide.csv", index=False)

    print("\nDONE")
    print("Saved:")
    print(" - kilimo_rice_beans_long.csv")
    print(" - kilimo_rice_beans_wide.csv")

    print("\nSample:")
    print(df.head(20))


if __name__ == "__main__":
    main()