import csv
import json
import requests
import time
import os

def scrape_train_data():
    input_file = '/Users/Taspol/Documents/sideProject/train_scrape/new/date_runhash_map_line31.csv'
    output_file = '/Users/Taspol/Documents/sideProject/train_scrape/new/station_delays_line31.csv'
    bearer_token = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpcCI6IjE4NC4yMi4zNC4yIiwidWEiOiJNb3ppbGxhLzUuMCAoTWFjaW50b3NoOyBJbnRlbCBNYWMgT1MgWCAxMF8xNV83KSBBcHBsZVdlYktpdC81MzcuMzYgKEtIVE1MLCBsaWtlIEdlY2tvKSBDaHJvbWUvMTQ4LjAuMC4wIFNhZmFyaS81MzcuMzYiLCJyb2xlIjoidmlld2VyIiwiaWF0IjoxNzc4MzQ0NjEyLCJleHAiOjE3NzgzNDQ5NzJ9.WEPQb3HZSiHOPw16DfEFDAjEOw3IMgkOK1s3Cy0Ay_A'
    
    headers = {
        'Authorization': f'Bearer {bearer_token}',
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/147.0.0.0 Safari/537.36'
    }

    results = []
    
    try:
        with open(input_file, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
    except Exception as e:
        print(f"Error reading input file: {e}")
        return

    print(f"Found {len(rows)} entries to scrape.")

    # To avoid losing data if it crashes, we'll write to the output file incrementally
    file_exists = os.path.isfile(output_file)
    with open(output_file, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['date', 'station_name', 'station_name_en', 'arr_delay', 'dep_delay', 'def_arrtime', 'act_arrtime', 'def_deptime', 'act_deptime', 'delay_cause_th', 'delay_cause_en'])

        for i, row in enumerate(rows):
            date = row['date']
            runhash = row['runhash']
            
            url = f"https://ttsview.railway.co.th/ttsAPI/specificTracking?qParam={runhash}&lang=th"
            
            try:
                print(f"[{i+1}/{len(rows)}] Scraping {date} ({runhash})...", end='\r')
                response = requests.get(url, headers=headers)
                
                if response.status_code == 200:
                    data = response.json()
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
                    else:
                        print(f"\nWarning: Unexpected data format for {date}: {type(data)}")
                else:
                    print(f"\nError: Received status code {response.status_code} for {date}")
                    if response.status_code == 401:
                        print("Bearer token might have expired.")
                        break
            
            except Exception as e:
                print(f"\nException for {date}: {e}")
            
            # Small delay to be polite to the server
            # time.sleep(0.1) 
    
    print(f"\nScraping complete. Results saved to {output_file}")

if __name__ == "__main__":
    scrape_train_data()
