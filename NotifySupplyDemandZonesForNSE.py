# --- EMA inclusion 
import yfinance as yf
import time
import requests
from datetime import datetime
import pytz
from datetime import datetime
import time
from datetime import datetime
from pytz import timezone
import pytz

# Parameters
SUPPLY_DEMAND_ZONE_WINDOW = 10  # Look-back period to calculate zones
ZONE_BUFFER = 0.002            # 0.3% buffer to define proximity
INDEXES = ["^NSEI", "^NSEBANK"]  # Nifty 50 and Bank Nifty and Nifty Finance Yahoo Finance Ticker
EMA_PERIOD = 21
TELEGRAM_BOT_TOKEN = "5771720913:AAH0A70f0BPtPjrOCTrhAb9LR7IGFBVt-oM" # Confidential
TELEGRAM_CHAT_ID = "-703180529"

def calculate_zones(data, window=10):
    """Calculate supply and demand zones based on historical data."""
    supply_zone = round(float(data['High'].rolling(window=window).max().iloc[-1]),2)
    demand_zone = round(float(data['Low'].rolling(window=window).min().iloc[-1]),2)
    print("Supply Zone : ", supply_zone)
    print("Demand Zone : ", demand_zone)
    return supply_zone, demand_zone

def get_live_price(data):
    """Fetch the current live price of an index from the last row of data."""
    return float(data['Close'].iloc[-1])

def get_nearest_strike_price(index_price, step):
    """Calculate the nearest strike price for a given index price."""
    return round(index_price / step) * step

def calculate_ema(data, period=21):
    """Calculate EMA for the data."""
    data[f"EMA_{period}"] = data['Close'].ewm(span=period, adjust=False).mean()
    return data

def send_telegram_message(message):
    """Send a notification message to Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

def notify_action(index, price, zone_type, zone_price, action, nearest_strike, ema):
    """Notify the action to be taken when price approaches a zone."""
    message = (
        f"**** DEMAND and SUPPLY ZONE ALERT ****\n"
        f"ALERT: {index}\n"
        f"Current Price: {price:.2f}\n"
        f"Near {zone_type} Zone at: {zone_price:.2f}\n"
        f"21 EMA: {ema:.2f}\n"
        f"Suggested Action: Buy {action}\n"
        f"Strike Price: {nearest_strike}\n"
    )
    print(message)
    send_telegram_message(message)

def check_market_conditions():
    """Check market conditions and send alerts."""
    IST = pytz.timezone("Asia/Kolkata")
    current_time = datetime.now(IST).time()
    if current_time >= datetime.strptime("09:15", "%H:%M").time() and current_time <= datetime.strptime("15:15", "%H:%M").time():
        print("Market is open in IST timezone")
        for index in INDEXES:
            # Fetch historical data
            data = yf.download(index, period="1mo", interval="5m")
            
            # Ensure data is valid
            if data.empty:
                print(f"No data available for {index}.")
                continue
            
            # Calculate 21 EMA
            data = calculate_ema(data, EMA_PERIOD)
            ema = round(data[f"EMA_{EMA_PERIOD}"].iloc[-1],2)
            print("EMA21 : ", ema)
            # Calculate supply and demand zones
            supply_zone, demand_zone = calculate_zones(data, window=SUPPLY_DEMAND_ZONE_WINDOW)
            
            # Fetch live price
            live_price = round(get_live_price(data),2)
            step = 50 if index == "^NSEI" else 100
            nearest_strike = get_nearest_strike_price(live_price, step)
            
            # Check proximity to zones and EMA conditions
            if live_price >= supply_zone * (1 - ZONE_BUFFER) and live_price < ema:
                notify_action(index, live_price, "supply", supply_zone, "PE", nearest_strike, ema)
            elif live_price <= demand_zone * (1 + ZONE_BUFFER) and live_price > ema:
                notify_action(index, live_price, "demand", demand_zone, "CE", nearest_strike, ema)
            else:
                print(f"{index} is not near any zone or doesn't satisfy EMA condition.")
    else:
        print("Market is closed. Alerts will resume during market hours.")

# # Schedule the job to run every 3 minutes
# schedule.every(1).minutes.do(check_market_conditions)

# if __name__ == "__main__":
#     while True:
#         schedule.run_pending()
#         time.sleep(6)  # Wait for a minute before the next iteration


if __name__ == "__main__":
    now_utc = datetime.now(timezone('UTC'))
    now_asia = now_utc.astimezone(timezone('Asia/Kolkata'))
    current_time = now_asia.strftime("%H:%M:%S")
    intTime = int(now_asia.strftime("%H"))  # Update hour dynamically

    print(f"Current Time: {current_time} | Monitoring Demand And Supply Zones...")
    while intTime>=9 and intTime <=14:
        check_market_conditions()
        #schedule.run_pending()
        if intTime >= 14:  # Exit after 2 PM
            print("Market is closed. Program exiting at:", current_time)
            break
        time.sleep(180)

