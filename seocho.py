import requests
import bs4
import json
import time
import os
import re
import click

centers = {
    # "040102": "서초", # 10/12까지 휴관
    "040602": "신반포",
    "040702": "방배",
    "040802": "서리풀",
    "040902": "내곡",
}

HOST_URL = "http://youngua.seocho.go.kr"
URL_PATTERN = "%s/yua/html/sub/index.php?pno=%s&listcnt=30&page=%d"
DATA_DIR="./data"
WORK_DIR="work"
OUTPUT_DIR="json"

def fetchHTML(url):
    resp = requests.get(url, headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:68.0) Gecko/20100101 Firefox/68.0',
    })
    resp.raise_for_status()
    resp.encoding='euc-kr'
    return resp.text

def parsePage(html):
    bs = bs4.BeautifulSoup(html, 'html.parser')
    return list(map(lambda x: x.attrs.get('href'), bs.select('td.board_item a')))

def parseItem(html, url=None):
    bs = bs4.BeautifulSoup(html, 'html.parser')
    image = bs.select('td.sub_gallery img')[0].attrs.get('src')
    image = image if image.startswith("http") else HOST_URL + image
    attrs = bs.select('td.pdl25 td.bdb')
    items = bs.select('table.tableF tr')

    item_status = []
    for item in items:
        try:
            item_status.append(dict(
                code=item.select('td.cell05c_r')[1].text.strip(),
                status=item.select('img')[0].attrs.get('alt').strip()
            ))
        except IndexError:
            continue

    title = attrs[1].text.strip()
    category = attrs[3].text.strip()
    age = attrs[5].text.strip()
    manufacturer = attrs[7].text.strip()
    lent_count = attrs[9].text.strip()[:-1]
    description = attrs[11].text.strip()

    return dict(
        image=image, title=title, category=category, age=age, manufacturer=manufacturer,
        lent_count=lent_count, description=description, items=item_status, url=url)

def scrapingSite(centers):
    now = int(time.time() / 3600) * 3600    # 한시간 단위
    itemcode = re.compile(".+itemcode=([a-zA-Z0-9]+).*")

    for center in centers:

        os.makedirs(f"{DATA_DIR}/{now}/{center}", exist_ok=True)

        print(f"\n{centers[center]}", end='', flush=True)
        
        i = 0
        while True:
            i += 1
            print(f"\n#{i}", end='', flush=True)
            page = fetchHTML(URL_PATTERN % (HOST_URL, center, i))
            item_urls = parsePage(page)

            print(f" -> {len(item_urls)} ", end='', flush=True)

            for item_url in item_urls:
                m = itemcode.match(item_url)
                code = m.group(1)
                filename = f"{DATA_DIR}/{now}/{center}/{code}.json"
                if os.path.exists(filename):
                    continue
                
                url = HOST_URL + item_url
                item = fetchHTML(url)
                parsed_item = parseItem(item, url)
                try:
                    with open(filename, "w") as f:
                        json.dump(parsed_item, f, ensure_ascii=False)
                except:
                    if os.path.exists(filename):
                        os.remove(filename)
                print('.', end='', flush=True)
            
            if len(item_urls) < 30:
                break


def mergeFiles(basepath, files):
    result = []
    center = centers[os.path.basename(basepath)]
    
    for file in files:
        with open(os.path.join(basepath, file), "r") as f:
            result.append(dict(json.load(f), **dict(branch=center)))
    
    with open(f"{WORK_DIR}/{center}.json", "w") as f:
        print(center)
        json.dump(result, f, ensure_ascii=False)


@click.group()
def cli():
    pass

@cli.command()
def extract():
    scrapingSite(centers)

@cli.command()
def convert():
    if not os.path.exists(WORK_DIR):
        os.makedirs(WORK_DIR)
    
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    for (dirpath, dirnames, filenames) in os.walk(DATA_DIR):
        if not filenames:
            continue
        mergeFiles(dirpath, filenames)

    for (dirpath, dirnames, filenames) in os.walk(f"{WORK_DIR}/"):
        result = []
        for filename in filenames:
            with open(os.path.join(dirpath, filename), "r") as f:
                result += json.load(f)
        with open(f"{OUTPUT_DIR}/seocho.json", "w") as f:
            json.dump(result, f, ensure_ascii=False)

if __name__ == '__main__':
    cli()