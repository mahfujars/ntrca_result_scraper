# ------------------------------------------------------------------------------
# Copyright (c) 2025 Mahfujar Rahman
# Author: Mahfujar Rahman Noyon <mrnoyon.cse@gmail.com>
# Created: 2025-06-05
# Description: Multithreaded scraper for NTRCA final results via Teletalk site.
# Handles retries, proxy rotation, user-agent spoofing, and async JSON saving.
# ------------------------------------------------------------------------------

import json
import requests
from lxml import html
from fake_useragent import UserAgent
import os
from retry import retry
import time
from datetime import timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed, wait, FIRST_COMPLETED
import threading
import sys
import queue
import random

stop_event = threading.Event()
save_lock = threading.Lock()
result_queue = queue.Queue()

with open('proxy.txt') as f:
    proxy_list = [line.strip() for line in f if line.strip()]
proxy = random.choice(proxy_list)
proxies = {
    'http': proxy,
    'https': proxy,
}

@retry(tries=30, delay=5)
def fetch_result(roll, headers, data, proxies):
    if stop_event.is_set():
        raise Exception("Stopped by user")
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

def process_roll(roll, index, total, start_time):
    if stop_event.is_set():
        return None
    
    try:
        now = time.time()
        elapsed = now - start_time
        processed_count = index
        rate = processed_count / elapsed if elapsed > 0 else 0
        remaining = total - processed_count
        eta_seconds = int(remaining / rate) if rate > 0 else 0
        eta_str = str(timedelta(seconds=eta_seconds)).split('.')[0]

        print(f"[{index}/{total}] Fetching roll: {roll} | Rate: {rate:.2f}/sec | ETA: {eta_str}")

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

        data = {
            'rollno': roll,
            'exam': '18:18th:2023:3',
            'yes': 'YES',
            'button2': 'Submit',
        }

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
            assert result_status[0] == 'SORRY! YOU ARE NOT QUALIFIED!'
            result_data['status'] = 'FAILED'

        result_queue.put(result_data)
        return result_data

    except Exception as e:
        print(f"❌ Error processing roll {roll}: {str(e)}")
        error_data = {
            'roll': roll,
            'status': 'ERROR',
            'error': str(e)
        }
        result_queue.put(error_data)
        return error_data

def save_results_worker(filename="all_results.json"):
    """Separate thread that handles all file saving operations"""
    temp_filename = filename + ".tmp"
    backup_filename = filename + ".bak"
    
    while not stop_event.is_set() or not result_queue.empty():
        try:
            results_to_save = []
            while True:
                try:
                    result = result_queue.get_nowait()
                    results_to_save.append(result)
                except queue.Empty:
                    break
            
            if not results_to_save:
                time.sleep(1)
                continue
                
            existing_results = []
            if os.path.exists(filename):
                with save_lock:
                    try:
                        with open(filename, 'r', encoding='utf-8') as f:
                            existing_results = json.load(f)
                    except (json.JSONDecodeError, IOError) as e:
                        print(f"⚠️ Error reading existing results: {e}")
                        if os.path.exists(backup_filename):
                            try:
                                with open(backup_filename, 'r', encoding='utf-8') as f:
                                    existing_results = json.load(f)
                            except Exception as e:
                                print(f"⚠️ Error reading backup: {e}")
                                existing_results = []
            
            roll_to_index = {r['roll']: i for i, r in enumerate(existing_results)}
            for new_result in results_to_save:
                if new_result['roll'] in roll_to_index:
                    existing_results[roll_to_index[new_result['roll']]] = new_result
                else:
                    existing_results.append(new_result)
            
            with save_lock:
                try:
                    if os.path.exists(filename):
                        os.replace(filename, backup_filename)
                    
                    with open(temp_filename, 'w', encoding='utf-8') as f:
                        json.dump(existing_results, f, ensure_ascii=False, indent=4)
                    
                    os.replace(temp_filename, filename)
                    print(f"💾 Saved {len(results_to_save)} results (total: {len(existing_results)})")
                    
                except Exception as e:
                    print(f"❌ Error saving results: {e}")
                    if os.path.exists(backup_filename):
                        try:
                            os.replace(backup_filename, filename)
                        except Exception as e:
                            print(f"❌ Error restoring backup: {e}")
            
        except Exception as e:
            print(f"❌ Unexpected error in save worker: {e}")
            time.sleep(5)

def main():
    try:
        with open("all_rolls.json", "r") as f:
            all_rolls = json.load(f)
    except Exception as e:
        print(f"❌ Failed to load roll numbers: {e}")
        return

    results_file = "all_results.json"
    if not os.path.exists(results_file):
        with open(results_file, 'w', encoding='utf-8') as f:
            json.dump([], f, ensure_ascii=False, indent=4)

    processed_rolls = set()
    try:
        with open(results_file, "r", encoding="utf-8") as f:
            existing_results = json.load(f)
            processed_rolls = {r['roll'] for r in existing_results}
    except Exception as e:
        print(f"⚠️ Error reading existing results: {e}")

    remaining_rolls = sorted(set(all_rolls) - processed_rolls)
    total = len(remaining_rolls)

    print(f"Total rolls to process: {total}")
    if not remaining_rolls:
        print("✅ All rolls already processed!")
        return
    saver_thread = threading.Thread(
        target=save_results_worker,
        args=(results_file,),
        daemon=True
    )
    saver_thread.start()

    start_time = time.time()

    try:
        with ThreadPoolExecutor(max_workers=100) as executor:
            futures = {
                executor.submit(process_roll, roll, idx, total, start_time): roll
                for idx, roll in enumerate(remaining_rolls, start=1)
            }
            for future in as_completed(futures):
                if stop_event.is_set():
                    break
                
                try:
                    result = future.result()
                    if result:
                        status = result.get('status', 'UNKNOWN')
                        print(f"ℹ️ Processed roll {result['roll']} - Status: {status}")
                except Exception as e:
                    print(f"❌ Error in future: {e}")

    except KeyboardInterrupt:
        print("\n⏸️ Ctrl+C detected! Stopping gracefully...")
        stop_event.set()
        
        print("💾 Finishing saving remaining results...")
        saver_thread.join(timeout=10)
        
        print("✅ Saved all results. Exiting program.")
        sys.exit(0)
        
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        stop_event.set()
        saver_thread.join(timeout=10)
        sys.exit(1)
        
    finally:
        stop_event.set()
        saver_thread.join(timeout=10)
        print("🎉 Processing completed!")

if __name__ == "__main__":
    main()