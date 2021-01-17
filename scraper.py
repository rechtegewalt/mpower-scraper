import re

import dataset
import get_retries
from bs4 import BeautifulSoup
from dateparser import parse

from hashlib import md5

db = dataset.connect("sqlite:///data.sqlite")

tab_incidents = db["incidents"]
tab_sources = db["sources"]
tab_chronicles = db["chronicles"]


tab_chronicles.upsert(
    {
        "iso3166_1": "DE",
        "iso3166_2": "DE-RP",
        "chronicler_name": "m*power",
        "chronicler_description": "Die Mobile Beratung für Betroffene rechter, rassistischer und antisemitischer Gewalt in Rheinland-Pfalz (m*power) hat im Mai 2017 ihre Beratungsarbeit aufgenommen. Für Betroffene rechter und rassistischer Gewalt gibt es damit in Rheinland-Pfalz ein landesweites Angebot, um diese entsprechend ihrer Bedarfe zu unterstützen.",
        "chronicler_url": "https://www.mpower-rlp.de/",
        "chronicle_source": "https://www.mpower-rlp.de/chronik-der-gewalt/chronik-der-uebergriffe.html",
    },
    ["chronicler_name"],
)


BASE_URL = "https://www.mpower-rlp.de/chronik-der-gewalt/chronik-der-uebergriffe.html"


def fetch(url):
    res = get_retries.get(url, verbose=True, max_backoff=128)
    if res is None:
        return None
    html_content = res.text
    soup = BeautifulSoup(html_content, "lxml")
    return soup


def process_report(report, url):
    date, city, description = [x.get_text().strip() for x in report.select("td")]

    # manual fixes
    date = (
        date.replace("04.11.", "04.11.2019")
        .replace("09.11.f.", "09.11.2019")
        .replace("f", "")
    )

    date = parse(date, languages=["de"])
    rg_id = (
        "mpower-"
        + md5((url + date.isoformat() + city + description).encode()).hexdigest()
    )

    data = dict(
        chronicler_name="m*power",
        description=description,
        city=city,
        date=date,
        rg_id=rg_id,
        url=url,
    )

    tab_incidents.upsert(data, ["rg_id"])


def process_page(page, url):
    first_row = True
    for row in page.select(".item-page tbody tr"):
        if first_row:
            first_row = False
            continue
        process_report(row, url)


url = BASE_URL
soup = fetch(url)
process_page(soup, url)
