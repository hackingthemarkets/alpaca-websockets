import websocket, json, requests, sys
from config import *
import dateutil.parser
from datetime import datetime

minutes_processed = {}
minute_candlesticks = []
current_tick = None
previous_tick = None
in_position = False

BASE_URL = "https://paper-api.alpaca.markets"
ACCOUNT_URL = "{}/v2/account".format(BASE_URL)
ORDERS_URL = "{}/v2/orders".format(BASE_URL)
POSITIONS_URL = "{}/v2/positions/{}".format(BASE_URL, SYMBOL)

HEADERS = {'APCA-API-KEY-ID': API_KEY, 'APCA-API-SECRET-KEY': SECRET_KEY}

def place_order(profit_price, loss_price):
    data = {
        "symbol": SYMBOL,
        "qty": 1,
        "side": "buy",
        "type": "market",
        "time_in_force": "gtc",
        "order_class": "bracket",
        "take_profit": {
            "limit_price": profit_price
        },
        "stop_loss": {
            "stop_price": loss_price
        }
    }

    r = requests.post(ORDERS_URL, json=data, headers=HEADERS)

    response = json.loads(r.content)

    print(response)

def on_open(ws):
    print("opened")
    auth_data = {
        "action": "auth",
        "params": API_KEY
    }

    ws.send(json.dumps(auth_data))

    channel_data = {
        "action": "subscribe",
        "params": TICKERS
    }

    ws.send(json.dumps(channel_data))


def on_message(ws, message):
    global current_tick, previous_tick, in_position

    previous_tick = current_tick
    current_tick = json.loads(message)[0]

    print(current_tick)
    print("=== Received Tick ===")
    print("{} @ {}".format(current_tick['t'], current_tick['bp']))
    tick_datetime_object = datetime.utcfromtimestamp(current_tick['t']/1000)
    tick_dt = tick_datetime_object.strftime('%Y-%m-%d %H:%M')

    print(tick_datetime_object.minute)
    print(tick_dt)

    if not tick_dt in minutes_processed:
        print("starting new candlestick")
        minutes_processed[tick_dt] = True
        print(minutes_processed)
    
        if len(minute_candlesticks) > 0:
            minute_candlesticks[-1]['close'] = previous_tick['bp']

        minute_candlesticks.append({
            "minute": tick_dt,
            "open": current_tick['bp'],
            "high": current_tick['bp'],
            "low": current_tick['bp']
        })
        

    if len(minute_candlesticks) > 0:
        current_candlestick = minute_candlesticks[-1]
        if current_tick['bp'] > current_candlestick['high']:
            current_candlestick['high'] = current_tick['bp']
        if current_tick['bp'] < current_candlestick['low']:
            current_candlestick['low'] = current_tick['bp']

    print("== Candlesticks ==")
    for candlestick in minute_candlesticks:
        print(candlestick)

    if len(minute_candlesticks) > 3:
        print("== there are more than 3 candlesticks, checking for pattern ==")
        last_candle = minute_candlesticks[-2]
        previous_candle = minute_candlesticks[-3]
        first_candle = minute_candlesticks[-4]

        print("== let's compare the last 3 candle closes ==")
        if last_candle['close'] > previous_candle['close'] and previous_candle['close'] > first_candle['close']:
            print("=== Three green candlesticks in a row, let's make a trade! ===")
            distance = last_candle['close'] - first_candle['open']
            print("Distance is {}".format(distance))
            profit_price = last_candle['close'] + (distance * 2)
            print("I will take profit at {}".format(profit_price))
            loss_price = first_candle['open']
            print("I will sell for a loss at {}".format(loss_price))

            if not in_position:
                print("== Placing order and setting in position to true ==")
                in_position = True
                place_order(profit_price, loss_price)
                sys.exit()
        else:
            print("No go")


def on_close(ws):
    print("closed connection")

socket = "wss://alpaca.socket.polygon.io/stocks"

ws = websocket.WebSocketApp(socket, on_open=on_open, on_message=on_message, on_close=on_close)
ws.run_forever()