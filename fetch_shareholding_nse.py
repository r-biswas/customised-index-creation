import asyncio
import os
import pandas as pd
from playwright.async_api import async_playwright
from datetime import datetime
from tqdm import tqdm
import sys

# YOUR WORKING LOGIC - Launching a fresh browser for every single symbol
async def fetch_shareholding_single(symbol):
    folder = "shareholding"
    file_path = os.path.join(folder, f"{symbol}_shareholding.csv")
    
    if os.path.exists(file_path):
        return # Cache hit

    try:
        async with async_playwright() as p:
            # Using Firefox as in your original working code
            browser = await p.firefox.launch(headless=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                locale="en-US"
            )
            page = await context.new_page()

            # Step 1: open homepage (get cookies)
            await page.goto("https://www.nseindia.com", wait_until="domcontentloaded", timeout=60000)
            await page.wait_for_timeout(3000)

            # Step 2: fetch shareholding data
            data = await page.evaluate(f"""
            async () => {{
                const res = await fetch(
                    '/api/corporate-share-holdings-master?index=equities&symbol={symbol}'
                );
                return await res.json();
            }}
            """)

            await browser.close()
            
            if data and isinstance(data, list):
                processed = []
                cutoff_year = datetime.now().year - 6
                for row in data:
                    try:
                        dt = datetime.strptime(row.get("date"), "%d-%b-%Y")
                        if dt.year < cutoff_year: continue
                        
                        promoter = float(row.get("pr_and_prgrp", 0))
                        public = float(row.get("public_val", 0))
                        if promoter == 0 and public == 0: continue
                        
                        processed.append({
                            "Date": dt.strftime("%Y-%m-%d"), 
                            "Promoter": promoter, 
                            "Public": public
                        })
                    except: continue
                
                if processed:
                    df = pd.DataFrame(processed).drop_duplicates().sort_values("Date", ascending=False)
                    df.to_csv(file_path, index=False)
                    return True
        return False
    except Exception as e:
        print(f"Error for {symbol}: {e}")
        return False

async def main():
    folder = "shareholding"
    if not os.path.exists(folder): os.makedirs(folder)
    
    if len(sys.argv) > 1:
        symbols = sys.argv[1:]
        print(f"Fetching shareholding for {len(symbols)} stocks using original logic...")
        
        # We run them sequentially to be safe, just like your manual test
        for sym in tqdm(symbols, desc="NSE Shareholding"):
            await fetch_shareholding_single(sym)
            # Short rest between browsers
            await asyncio.sleep(1)
        
        print("Done.")

if __name__ == "__main__":
    asyncio.run(main())
