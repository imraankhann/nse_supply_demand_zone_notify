import yfinance as yf
import schedule
import time
import requests
from datetime import datetime
import time
from datetime import datetime
from pytz import timezone

# Parameters
SUPPLY_DEMAND_ZONE_WINDOW = 10  # Look-back period to calculate zones
ZONE_BUFFER = 0.001            # 0.3% buffer to define proximity
INDEXES = ["^NSEI", "^NSEBANK"]  # Nifty 50 and Bank Nifty and Nifty Finance Yahoo Finance Tickers  ,"NIFTY_FIN_SERVICE.NS"
TELEGRAM_BOT_TOKEN = "5771720913:AAH0A70f0BPtPjrOCTrhAb9LR7IGFBVt-oM"  # Replace with your Telegram bot token
TELEGRAM_CHAT_ID = "-703180529"      # Replace with your Telegram chat ID

def calculate_zones(data, window=10):
    """Calculate supply and demand zones based on historical data."""
    supply_zone = float(data['High'].rolling(window=window).max().iloc[-1])
    print("Supply Zone : ", supply_zone)
    demand_zone = float(data['Low'].rolling(window=window).min().iloc[-1])
    print("Demand Zone : ", demand_zone)
    return supply_zone, demand_zone

def get_live_price(data):
    """Fetch the current live price of an index from the last row of data."""
    return float(data['Close'].iloc[-1])

def send_telegram_message(message):
    """Send a notification message to Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

def notify_action(index, price, zone_type, zone_price, action):
    """Notify the action to be taken when price approaches a zone."""
    message = (
        f"ALERT: {index} current price {price:.2f} is near {zone_type} zone at {zone_price:.2f}. "
        f"Suggested action: Buy {action}."
    )
    print(message)
    send_telegram_message(message)

def check_market_conditions():
    """Check market conditions and send alerts."""
    current_time = datetime.now().time()
    if current_time >= datetime.strptime("09:15", "%H:%M").time() and current_time <= datetime.strptime("15:15", "%H:%M").time():
        for index in INDEXES:
            # Fetch historical data
            data = yf.download(index, period="1mo", interval="1h")
            
            # Ensure data is valid
            if data.empty:
                print(f"No data available for {index}.")
                continue
            
            # Calculate supply and demand zones
            supply_zone, demand_zone = calculate_zones(data, window=SUPPLY_DEMAND_ZONE_WINDOW)
            
            # Fetch live price
            live_price = get_live_price(data)
            
            # Check proximity to zones
            if live_price >= supply_zone * (1 - ZONE_BUFFER):
                notify_action(index, live_price, "supply", supply_zone, "PE")
            elif live_price <= demand_zone * (1 + ZONE_BUFFER):
                notify_action(index, live_price, "demand", demand_zone, "CE")
    else:
        print("Market is closed. Alerts will resume during market hours.")

# Schedule the job to run every 3 minutes
schedule.every(3).minutes.do(check_market_conditions)

if __name__ == "__main__":
    now_utc = datetime.now(timezone('UTC'))
    now_asia = now_utc.astimezone(timezone('Asia/Kolkata'))
    current_time = now_asia.strftime("%H:%M:%S")
    intTime = int(now_asia.strftime("%H"))  # Update hour dynamically

    print(f"Current Time: {current_time} | Monitoring Demand And Supply Zones...")
    while intTime>=8 and intTime <=14:
        schedule.run_pending()
        if intTime >= 14:  # Exit after 2 PM
            print("Market is closed. Program exiting at:", current_time)
            break
        time.sleep(60)
