import requests
import time
from datetime import datetime, timedelta
import pytz
import yfinance as yf

# Telegram Bot Configuration
TELEGRAM_TOKEN = "5771720913:AAH0A70f0BPtPjrOCTrhAb9LR7IGFBVt-oM"
TELEGRAM_CHAT_ID = "-703180529"

# NSE Index Symbols
INDEXES = {"^NSEI": "Nifty 50", "^NSEBANK": "Bank Nifty"}

# Zigzag parameters
ZIGZAG_LEN = 9
FIB_FACTOR = 0.33
ZONE_BUFFER = 0.003  # 0.3%

# Strike price step (50 for Nifty, 100 for Bank Nifty)
STRIKE_PRICE_STEP = {"^NSEI": 50, "^NSEBANK": 100}

# IST timezone
IST = pytz.timezone("Asia/Kolkata")


def send_telegram_message(message):
    """
    Sends a message to a Telegram chat.
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
        print(f"Sent message: {message}")
    except Exception as e:
        print(f"Failed to send message: {e}")


def get_nearest_strike_price(price, step):
    """
    Calculate the nearest strike price.
    """
    return round(price / step) * step


def calculate_zones(data):
    """
    Calculate high/low zones for supply and demand as scalar values.
    """
    if len(data) < ZIGZAG_LEN:
        # Not enough data to calculate zones
        return None, None

    # Ensure scalar values are extracted
    high_zone = data['High'].rolling(window=ZIGZAG_LEN).max().iloc[-1]
    low_zone = data['Low'].rolling(window=ZIGZAG_LEN).min().iloc[-1]
    return high_zone, low_zone



def fetch_live_data(symbol):
    """
    Fetch live index data from Yahoo Finance.
    """
    try:
        data = yf.download(symbol, period="1d", interval="1m")
        if not data.empty:
            live_price = data['Close'].iloc[-1]
            return data, live_price
        else:
            return None, None
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None, None


def main():
    current_time = datetime.now(IST).time()
    print("Current Time : ", current_time)
    # Run between 9:15 AM and 3:15 PM IST
    while datetime.strptime("09:15", "%H:%M").time() <= current_time <= datetime.strptime("11:55", "%H:%M").time():
        current_time = datetime.now(IST).time()
        for symbol, name in INDEXES.items():
            data, live_price = fetch_live_data(symbol)
            if data is None or live_price is None:
                print(f"Data unavailable for {name}. Skipping...")
                continue

            high_zone, low_zone = calculate_zones(data)
            if high_zone is None or low_zone is None:
                print(f"Not enough data for {name} to calculate zones. Skipping...")
                continue

            # Ensure zones are scalar
            high_zone = round(float(high_zone),2)
            low_zone = round(float(low_zone),2)
            live_price = round(float((data['Close'].iloc[-1])),2)

            # Check for conditions
            if live_price >= high_zone * (1 - ZONE_BUFFER):  # Near BE-OB or BE-BB zone
                strike_price = get_nearest_strike_price(live_price, STRIKE_PRICE_STEP[symbol])
                message = f"REVERSAL ALERT: {name} price {live_price:.2f} near Resistance zone ({high_zone:.2f}). Buy PE at {strike_price}."
                send_telegram_message(message)

            elif live_price <= low_zone * (1 + ZONE_BUFFER):  # Near BU-OB or BU-BB zone
                strike_price = get_nearest_strike_price(live_price, STRIKE_PRICE_STEP[symbol])
                message = f"REVERSAL ALERT: {name} price {live_price:.2f} near Support zone ({low_zone:.2f}). Buy CE at {strike_price}."
                send_telegram_message(message)
        # Sleep for 3 minutes
        time.sleep(180)
        print("Wait for 3 min..!")
        
if __name__ == "__main__":
    main()
