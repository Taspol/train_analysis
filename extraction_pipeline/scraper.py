import csv
import json
import requests
import time
import os
from typing import List, Dict, Any

class TrainScraper:
    """Class to handle train delay data extraction from TTS API."""
    
    BASE_URL = "https://ttsview.railway.co.th/ttsAPI/specificTracking"
    
    def __init__(self, bearer_token: str):
        self.headers = {
            'Authorization': f'Bearer {bearer_token}',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36'
        }
    
    def scrape_by_runhash(self, runhash: str) -> List[Dict[str, Any]]:
        """Scrape tracking data for a specific runhash."""
        url = f"{self.BASE_URL}?qParam={runhash}&lang=th"
        try:
            response = requests.get(url, headers=self.headers)
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                raise Exception("Bearer token expired or invalid (401).")
            else:
                print(f"Error: Status code {response.status_code}")
                return []
        except Exception as e:
            print(f"Connection error for {runhash}: {e}")
            return []

    def batch_scrape(self, input_file: str, output_file: str):
        """Perform batch scraping from an input CSV to an output CSV."""
        if not os.path.exists(input_file):
            print(f"Input file not found: {input_file}")
            return

        with open(input_file, mode='r', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))

        print(f"Starting batch scrape of {len(rows)} entries.")
        
        with open(output_file, mode='w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['date', 'station_name', 'station_name_en', 'arr_delay', 'dep_delay', 'def_arrtime', 'act_arrtime', 'def_deptime', 'act_deptime', 'delay_cause_th', 'delay_cause_en'])

            for i, row in enumerate(rows):
                date = row.get('date')
                runhash = row.get('runhash')
                print(f"[{i+1}/{len(rows)}] Scraping {date}...", end='\r')
                
                data = self.scrape_by_runhash(runhash)
                if isinstance(data, list):
                    for station in data:
                        writer.writerow([
                            date,
                            station.get('stop_name'),
                            station.get('stop_name_en'),
                            station.get('act_arr_late'),
                            station.get('act_dep_late'),
                            station.get('def_arrtime'),
                            station.get('act_arrtime'),
                            station.get('def_deptime'),
                            station.get('act_deptime'),
                            station.get('delay_cause_th'),
                            station.get('delay_cause_en')
                        ])
                
        print(f"\nScrape complete. Data saved to {output_file}")
