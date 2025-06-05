# ------------------------------------------------------------------------------
# Copyright (c) 2025 Mahfujar Rahman
# Author: Mahfujar Rahman Noyon <mrnoyon.cse@gmail.com>
# Created: 2025-06-05
# Description: This script fetches NTRCA final exam results from the official
# Teletalk website for a list of roll numbers. It handles retries, proxy
# rotation, result parsing, and incremental JSON saving.
# ------------------------------------------------------------------------------


import json
import requests
from lxml import html
from fake_useragent import UserAgent
import os
from retry import retry
import time
import random
from datetime import timedelta, datetime


@retry(tries=30, delay=5)
def fetch_result(roll, headers, data, proxies):
    try:
        response = requests.post(
            'http://ntrca.teletalk.com.bd/result/index.php',
            headers=headers,
            data=data,
            verify=False,
            proxies=proxies,
            timeout=15
        )
        if not response.content.strip():
            raise Exception(f"Empty response for roll {roll}")
        return response
    except Exception as e:
        print(f"❌ Retry error for roll {roll}: {e}")
        raise


with open("all_rolls.json", "r") as f:
    all_rolls = json.load(f)

all_results = []
processed_rolls = set()
results_file = "all_results.json"

if os.path.exists(results_file):
    with open(results_file, "r", encoding="utf-8") as f:
        all_results = json.load(f)
        processed_rolls = {r['roll'] for r in all_results}

remaining_rolls = sorted(set(all_rolls) - processed_rolls)

headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'en-US,en;q=0.9',
    'Cache-Control': 'max-age=0',
    'Connection': 'keep-alive',
    'Content-Type': 'application/x-www-form-urlencoded',
    'Origin': 'http://ntrca.teletalk.com.bd',
    'Referer': 'http://ntrca.teletalk.com.bd/result/index.php',
    'Upgrade-Insecure-Requests': '1',
    'User-Agent': UserAgent().random,
}


with open('proxy.txt') as f:
    proxy_list = [line.strip() for line in f if line.strip()]
proxy = random.choice(proxy_list)
proxies = {
    'http': proxy,
    'https': proxy,
}

try:
    response = requests.get('http://httpbin.org/ip', proxies=proxies, timeout=10)
    print(response.text)
except Exception as e:
    raise Exception("Proxy test failed:", e)

start_time = time.time()

for roll in remaining_rolls:
    i = all_rolls.index(roll) + 1
    j = remaining_rolls.index(roll) + 1
    now = time.time()
    elapsed = now - start_time
    rate = j / elapsed if elapsed > 0 else 0
    remaining = len(remaining_rolls) - i
    eta_seconds = int(remaining / rate) if rate > 0 else 0
    eta_str = str(timedelta(seconds=eta_seconds)).split('.')[0] 

    #print(f"[{i}/{len(all_rolls)}] Fetching roll: {roll}")
    print(f"[{i}/{len(all_rolls)}] Fetching roll: {roll} | Rate: {rate:.2f}/sec | ETA: {eta_str}")
    data = {
        'rollno': roll,
        'exam': '18:18th:2023:3',
        'yes': 'YES',
        'button2': 'Submit',
    }

    try:
        response = fetch_result(roll, headers, data, proxies)

        doc = html.fromstring(response.content)
        result_status = doc.xpath('//span[@class="red12bold"]/text()')

        result_data = {
            'roll': roll,
            'status': None,
            'position': None,
            'subject': None,
            'personal_details': {}
        }

        if result_status and result_status[0] == 'CONGRATULATIONS, PASSED THE FINAL EXAM':
            result_data['status'] = 'PASSED'
            td = doc.xpath('//span[@class="red12bold"]/parent::td')[0]

            position = td.xpath('./span[@class="black12bold"][2]/text()')[0]
            result_data['position'] = position.strip()

            subject = td.xpath('./span[@class="black12bold"][3]/text()')[0]
            result_data['subject'] = subject.strip()

            personal_details = td.xpath('./text()')
            cleaned_details = [line.strip() for line in personal_details if line.strip()]
            details_dict = {}

            for line in cleaned_details:
                if ':' in line:
                    key, value = line.split(':', 1)
                    if key == 'Roll':
                        continue
                    details_dict[key.strip()] = value.strip()

            result_data['personal_details'] = details_dict
        else:
            assert result_status[0] =='SORRY! YOU ARE NOT QUALIFIED!'
            result_data['status'] = 'FAILED'

        all_results.append(result_data)

        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump(all_results, f, ensure_ascii=False, indent=4)

    except Exception as e:
        print(f"❌ Error for roll {roll}: {e}")
        if str(e) == 'Document is empty':
            with open('error.html', 'w' ) as f:
                f.write(response.text)
        break
