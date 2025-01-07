# --- BB, EMA and ADX inclusion 
import yfinance as yf
import time
import requests
from datetime import datetime
import pytz
from pytz import timezone
from ta.momentum import RSIIndicator
import pandas as pd
import numpy as np
from ta.trend import ADXIndicator

# Parameters          # 0.04% buffer to define proximity
INDEXES = ["^NSEI", "^NSEBANK"]  # Nifty 50 and Bank Nifty and Nifty Finance Yahoo Finance Ticker
EMA_PERIOD = 5
BOLLINGER_PERIOD = 20
TELEGRAM_BOT_TOKEN = "5817461626:AAHp1IIIMkQGWFTqIuu84lYOoxlO8KS7CZo"
TELEGRAM_CHAT_ID = "@swingTradeScreenedStocks"

def calculate_zones(data, window=10):
    """Calculate supply and demand zones based on historical data."""
    supply_zone = round(float(data['High'].rolling(window=window).max().iloc[-1]),2)
    demand_zone = round(float(data['Low'].rolling(window=window).min().iloc[-1]),2)
    return supply_zone, demand_zone

def get_live_price(data):
    """Fetch the current live price of an index from the last row of data."""
    return float(data['Close'].iloc[-1])

def get_nearest_strike_price(index_price, step):
    """Calculate the nearest strike price for a given index price."""
    return round(index_price / step) * step

def calculate_ema(data, period=5):
    """Calculate EMA for the data."""
    data[f"EMA_{period}"] = data['Close'].ewm(span=period, adjust=False).mean()
    return data


def calculate_bollinger_bands(data, period=20):
    """Calculate Bollinger Bands."""
    data['SMA'] = data['Close'].rolling(window=period).mean()
    data['STD'] = data['Close'].rolling(window=period).std()
    data['Upper_Band'] = data['SMA'] + (1.5 * data['STD'])
    data['Lower_Band'] = data['SMA'] - (1.5 * data['STD'])
    return data

def get_current_adr(data):
    """Calculate the current Average Daily Range (ADR)."""
    data['Daily_Range'] = data['High'] - data['Low']
    adr = data['Daily_Range'].mean()
    return round(adr, 2)

def calculate_adx(data, period=14):
    """Calculate the ADX (Average Directional Index) value."""
    # Ensure 'High', 'Low', and 'Close' are 1-dimensional pandas Series
    high = data['High'].squeeze().astype(float)
    low = data['Low'].squeeze().astype(float)
    close = data['Close'].squeeze().astype(float)
    
    # Check if dimensions are correct
    if high.ndim != 1 or low.ndim != 1 or close.ndim != 1:
        raise ValueError("Input data columns must be 1-dimensional pandas Series.")
    
    # Calculate ADX
    adx_indicator = ADXIndicator(high=high, low=low, close=close, window=period)
    data['ADX'] = adx_indicator.adx()
    return data

def get_current_adx(data, period=14):
    """Fetch the current ADX value in IST timezone."""
    # Calculate ADX for the data
    adx_data = calculate_adx(data, period)
    
    # Fetch the latest ADX value
    current_adx = round(adx_data['ADX'].iloc[-1], 2)
    
    # Fetch the current time in IST
    utc_now = datetime.now(timezone('UTC'))
    ist_now = utc_now.astimezone(timezone('Asia/Kolkata'))
    timestamp = ist_now.strftime("%d-%m-%Y %H:%M:%S")
    return current_adx

def send_telegram_message(message):
    """Send a notification message to Telegram."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Failed to send Telegram message: {e}")

def notify_action(index, price, action, nearest_strike, ema, adx, lower_band, upper_band):
    """Notify the action to be taken when price approaches a zone."""
    utc_now = datetime.now(timezone('UTC'))
    ist_now = utc_now.astimezone(timezone('Asia/Kolkata'))
    timestamp = ist_now.strftime("%d-%m-%Y %H:%M")
    message = (
        f"=====================\n"
        f"BB, EMA & ADX \n"
        f"=====================\n"
        f"Notified At : {timestamp}\n"
        f"ALERT: {index}\n"
        f"Current Price: {price:.2f}\n"
        f"5 EMA: {ema:.2f}\n"
        f"ADX: {adx:.2f}\n"
        f"Lower Bollinger Band: {lower_band:.2f}\n"
        f"Upper Bollinger Band: {upper_band:.2f}\n"
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
    if current_time >= datetime.strptime("09:15", "%H:%M").time() and current_time <= datetime.strptime("13:59", "%H:%M").time():
        print("Market is open in IST timezone : ", current_time)
        for index in INDEXES:
            # Fetch historical data
            data = yf.download(index, period="1mo", interval="5m")

            # Ensure data is valid
            if data.empty:
                print(f"No data available for {index}.")
                continue

            # Calculate technical indicators
            ema_data = calculate_ema(data, EMA_PERIOD)
            ema = round(ema_data[f"EMA_{EMA_PERIOD}"].iloc[-1], 2)

            #rsi_data = calculate_rsi(data, RSI_PERIOD)
            #correct_rsi = float(round(rsi_data['RSI'].iloc[-1], 2))

            bollinger_data = calculate_bollinger_bands(data, BOLLINGER_PERIOD)
            lower_band = round(bollinger_data['Lower_Band'].iloc[-1], 2)
            upper_band = round(bollinger_data['Upper_Band'].iloc[-1], 2)
            lower_band_minus = lower_band - 10
            lower_band_plus = lower_band + 10
            upper_band_minus = upper_band - 10
            upper_band_plus = upper_band + 10
            adr = get_current_adr(data)
            adx = get_current_adx(data, period=14)

            live_price = round(get_live_price(data), 2)
            step = 50 if index == "^NSEI" else 100
            nearest_strike = get_nearest_strike_price(live_price, step)

            print("********************* DATA PRINT STARTED ***********************")
            data_dic = {
                "Index =": index,
                "Current Time =": current_time,
                "CMP =": live_price,
                "5 EMA =": ema,
                "ADR =": adr,
                "Lower Band =": lower_band,
                "Upper Band =": upper_band,
                "ADX = ": adx
            }
            for key, value in data_dic.items():
                print(key, '\t', value)
            print("********************* DATA PRINT ENDED ***********************")

            
            if live_price < ema and (lower_band_minus <= live_price <= lower_band_plus) and adx > 23 :
                notify_action(index, live_price, "CE", nearest_strike, ema, adx, lower_band, upper_band)
                time.sleep(120)
            elif live_price > ema and (upper_band_minus <= live_price <= upper_band_plus) and adx > 23 : 
                notify_action(index, live_price, "PE", nearest_strike, ema, adx, lower_band, upper_band) 
                time.sleep(120)
            else:
                print(f"{index} is not near any bollinger bands or doesn't satisfy EMA or ADX conditions")
    else:
        print("Market is closed. Alerts will resume during market hours exiting now..!")
        exit()


if __name__ == "__main__":
    now_utc = datetime.now(timezone('UTC'))
    now_asia = now_utc.astimezone(timezone('Asia/Kolkata'))
    current_time = now_asia.strftime("%H:%M:%S")
    intTime = int(now_asia.strftime("%H"))  # Update hour dynamically
    print(f"Current Time: {current_time} | Monitoring BollingerBands, EMA, ADX Zones...")
    while intTime>=9 and intTime <=13:
        check_market_conditions()
        #schedule.run_pending()
        if intTime > 13:  # Exit after 2 PM
            print("Market is closed. Program exiting at:", current_time)
            break
        time.sleep(180)
