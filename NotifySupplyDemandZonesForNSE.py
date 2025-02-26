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
from ta.momentum import RSIIndicator
import pandas as pd

# Parameters
SUPPLY_DEMAND_ZONE_WINDOW = 10  # Look-back period to calculate zones
ZONE_BUFFER = 0.0004            # 0.04% buffer to define proximity
INDEXES = ["^NSEI", "^NSEBANK"]  # Nifty 50 and Bank Nifty and Nifty Finance Yahoo Finance Ticker
EMA_PERIOD = 21
# TELEGRAM_BOT_TOKEN = "5771720913:AAH0A70f0BPtPjrOCTrhAb9LR7IGFBVt-oM" # Confidential
# TELEGRAM_CHAT_ID = "-703180529"
TELEGRAM_BOT_TOKEN = "5817461626:AAHp1IIIMkQGWFTqIuu84lYOoxlO8KS7CZo"
TELEGRAM_CHAT_ID = "@swingTradeScreenedStocks"
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30


def calculate_zones(data, window=10):
    """Calculate supply and demand zones based on historical data."""
    supply_zone = round(float(data['High'].rolling(window=window).max().iloc[-1]),2)
    demand_zone = round(float(data['Low'].rolling(window=window).min().iloc[-1]),2)
    # supply_zone = round(float(data['High'].rolling(window=window).max().iloc[-1]), 2)
    # demand_zone = round(float(data['Low'].rolling(window=window).max().iloc[-1]), 2)
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

def calculate_rsi(data, period=14):
    """Calculate RSI for the data."""
    ist = pytz.timezone("Asia/Kolkata")
    if data.index.tzinfo is None:
        data.index = data.index.tz_localize("UTC").tz_convert(ist)
    else:
        data.index = data.index.tz_convert(ist)
    if 'Close' not in data.columns:
        raise ValueError("Input data must have a 'Close' column.")

    # Use the 'Close' column to calculate RSI
    close = data['Close']

    delta = close.diff()
    dUp = delta.clip(lower=0)  # Keep only positive changes
    dDown = -delta.clip(upper=0)  # Keep only negative changes (convert to positive)

    RolUp = dUp.rolling(window=period).mean()
    RolDown = dDown.rolling(window=period).mean()

    RS = RolUp / RolDown
    rsi = 100.0 - (100.0 / (1.0 + RS))

    data['RSI'] = rsi  # Add RSI to the DataFrame
    #print("RSI DATA : ", data['RSI'])
    return data


def send_telegram_message(message):
    """Send a notification message to Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

def notify_action(index, price, zone_type, zone_price, action, nearest_strike, ema,rsi):
    """Notify the action to be taken when price approaches a zone."""
    utc_now = datetime.now(timezone('UTC'))
    ist_now = utc_now.astimezone(timezone('Asia/Kolkata'))
    timestamp = ist_now.strftime("%d-%m-%Y %H:%M")
    message = (
        f"=====================\n"
        f"DEMAND & SUPPLY ZONES\n"
        f"=====================\n"
        f"Notified At : {timestamp}\n"
        f"ALERT: {index}\n"
        f"Current Price: {price:.2f}\n"
        f"Near {zone_type} Zone at: {zone_price:.2f}\n"
        f"21 EMA: {ema:.2f}\n"
        f"RSI: {rsi:.2f}\n"
        f"Suggested Action: Buy {action}\n"
        f"Strike Price: {nearest_strike}\n"
        f"=====================\n"
    )
    print(message)
    send_telegram_message(message)

def check_market_conditions():
    """Check market conditions and send alerts."""
    IST = pytz.timezone("Asia/Kolkata")
    current_time = datetime.now(IST).time()
    if current_time >= datetime.strptime("09:15", "%H:%M").time() and current_time <= datetime.strptime("14:45", "%H:%M").time():
        print("Market is open in IST timezone : ", current_time)
        for index in INDEXES:
            # Fetch historical data
            data = yf.download(index, period="1mo", interval="5m")
            
            # Ensure data is valid
            if data.empty:
                print(f"No data available for {index}.")
                continue
            
            # Calculate 21 EMA
            ema_data = calculate_ema(data, EMA_PERIOD)
            ema = round(ema_data[f"EMA_{EMA_PERIOD}"].iloc[-1],2)
            rsi_data = calculate_rsi(data,14)
            correct_rsi = float(round(rsi_data['RSI'].iloc[-1], 2))
            #correct_rsi = rsi - 15
            print("RSI : ",correct_rsi)
            # Calculate supply and demand zones
            supply_zone, demand_zone = calculate_zones(data, window=SUPPLY_DEMAND_ZONE_WINDOW)
            positive_supply_zone_buffer = round(supply_zone * (1 + ZONE_BUFFER),2)
            negative_supply_zone_buffer = round(supply_zone * (1 - ZONE_BUFFER),2)
            positive_demand_zone_buffer = round(demand_zone * (1 + ZONE_BUFFER),2)
            negative_demand_zone_buffer = round(demand_zone * (1 - ZONE_BUFFER),2)
            # Fetch live price
            live_price = round(get_live_price(data),2)
            step = 50 if index == "^NSEI" else 100
            nearest_strike = get_nearest_strike_price(live_price, step)
            print("********************* DATA PRINT STARTED ***********************")
            data_dic = {"Index =":index,
                        "currentTime =":current_time,
                        "cmp =": live_price,
                        "negative_demand_buffer_zone =": negative_demand_zone_buffer,
                        "positive_demand_buffer_zone =": positive_demand_zone_buffer,
                        "negative_supply_buffer_zone =": negative_supply_zone_buffer,
                        "positive_supply_buffer_zone =": positive_supply_zone_buffer,
                        "demand_zone =":demand_zone,
                        "supply_zone =":supply_zone,
                        "21EMA =":float(ema),
                        "RSI =":float(correct_rsi)
                        }
            for key,value in data_dic.items():
                print(key,'\t',value)
            print("********************* DATA PRINT ENDED ***********************")
    
            # Check proximity to zones and EMA conditions
            # Removing ema condn  and live_price < ema in if and and live_price > ema in else
            if negative_demand_zone_buffer <= live_price <= positive_demand_zone_buffer and correct_rsi < RSI_OVERSOLD:
                notify_action(index, live_price, "demand", demand_zone, "CE", nearest_strike, ema, correct_rsi)
                time.sleep(120)
            elif negative_supply_zone_buffer <= live_price <= positive_supply_zone_buffer and correct_rsi > RSI_OVERBOUGHT:
                notify_action(index, live_price, "supply", supply_zone, "PE", nearest_strike, ema, correct_rsi)
                time.sleep(120)
            else:
                print(f"{index} is not near any zone or doesn't satisfy EMA condition.")
    else:
        print("Market is closed. Alerts will resume during market hours exiting now..!")
        exit()


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

