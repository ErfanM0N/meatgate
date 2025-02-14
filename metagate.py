from flask import Flask, request, jsonify
import MetaTrader5 as mt5  
from datetime import datetime, timedelta
from collections import defaultdict
from decimal import Decimal

app = Flask(__name__)


def init_metatrader(login: int, server: str, password: str):
    if not mt5.initialize(login=login, server=server, password=password):
        error_code = mt5.last_error()
        return {"success": False, "error": f"Initialize failed, error code = {error_code}"}
    return {"success": True, "message": "MetaTrader initialized successfully"}


def format_time(timestamp, offset):
    local_time = datetime.utcfromtimestamp(timestamp) + timedelta(seconds=offset)
    return local_time.strftime('%Y-%m-%d %H:%M:%S')


def get_offset():
    tick = mt5.symbol_info_tick('XAUUSD')
    server_time = datetime.utcfromtimestamp(tick.time)
    local_time = datetime.now()

    local_time = local_time.replace(microsecond=0)

    time_diff = (local_time - server_time).total_seconds()

    return int(time_diff - (time_diff % 30))


def get_positions() -> list:
    positions = mt5.positions_get()

    position_details = []

    if positions == ():
        return []
    elif positions is None:
        return None
    
    else:
        offset = get_offset()
        for position in positions:
            position_info = {
            "Ticket": position.ticket,
            "Symbol": position.symbol,
            "Volume": Decimal(str(round(position.volume, 2))),
            "Type": "buy" if position.type == 0 else "sell",
            "Profit": Decimal(str(round(position.profit, 2))),
            "Time": format_time(position.time, offset),
            "Price Open": Decimal(str(round(position.price_open, 2))),
            "Current Price": Decimal(str(round(position.price_current, 2))),
            "Swap": Decimal(str(round(position.swap, 2))),
            }
            position_details.append(position_info)
    
        return position_details


def get_aggregated_positions():
    positions = get_positions()

    if positions is None:
        return None
     
    aggregated_data = defaultdict(lambda: {'Net Volume': 0, 'Total Profit': 0, 'Total Swap': 0, 'Total Open': 0})

    for position in positions:
        symbol = position['Symbol']
        aggregated_data[symbol]['Total Open'] += position['Volume']

        if position['Type'] == 'buy':
            aggregated_data[symbol]['Net Volume'] += position['Volume']
        else: 
            aggregated_data[symbol]['Net Volume'] -= position['Volume']
    
        aggregated_data[symbol]['Total Profit'] += position['Profit']
        aggregated_data[symbol]['Total Swap'] += position['Swap']



    result = []
    for symbol, data in aggregated_data.items():

        result.append({
            'Symbol': symbol,
            'Net Volume': data['Net Volume'],
            'Total Profit': data['Total Profit'],
            'Total Open': data['Total Open'],
            'Total Swap': data['Total Swap'],
        })

    return result


def get_balance_info():
    account_info = mt5.account_info()
    if account_info is not None:
        account_info_dict = {
            "Balance": account_info.balance,
            "Profit": account_info.profit,
            "Equity": account_info.equity,
            "Margin": account_info.margin,
            "Margin_free": account_info.margin_free,
            "Margin_level": account_info.margin_level
        }
        return account_info_dict
    else:
        return None
    

def get_orders() -> list:
    orders = mt5.orders_get()

    order_details = []

    if orders == ():
        return []
    elif orders is None:
        return None
    
    else:
        offset = get_offset()
        for order in orders:
            order_info = {
            "Ticket": order.ticket,
            "Symbol": order.symbol,
            "Volume": Decimal(str(round(order.volume_current, 2))),
            "Type": "buy limit" if order.type == 2 else "sell limit",
            "Time": format_time(order.time_setup, offset),
            "Price Open": Decimal(str(round(order.price_open, 2))),
            "Current Price": Decimal(str(round(order.price_current, 2))),
            }
            order_details.append(order_info)
    
        return order_details
    

def get_price(symbol: str):
    info = mt5.symbol_info_tick(symbol)
    if not info:
        return None

    return {'Bid': info.bid, 'Ask': info.ask}


def get_position_type_volume(ticket: int):
    positions = get_positions()
    if positions is None:
        return None, None, False
    for position in positions:
        if position['Ticket'] == ticket:
            return position['Type'], position['Volume'], True
    return None, None, True


def get_aggregated_volume_by_symbol(symbol:str) -> Decimal:
    aggregated_positions = get_aggregated_positions() or []

    for aggregated_position in aggregated_positions:
        if aggregated_position['Symbol'] == symbol:
            return aggregated_position['Total Volume']
        
    return Decimal(0.0)


def close_position(symbol: str, ticket: int, volume: float = 0, magic: int = 0, deviation: int = 50):
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "position": ticket,
        "volume": volume,
        "deviation": deviation,
        "magic": magic,
    }

    type, position_volume, is_connected = get_position_type_volume(ticket)
    if not is_connected:
        return {"success": False, "message": "Check connection to metatrader"}
    if type == 'buy':
        request["type"] = mt5.ORDER_TYPE_SELL
        request["price"] = mt5.symbol_info_tick(symbol).bid
    elif type == 'sell':
        request["type"] = mt5.ORDER_TYPE_BUY
        request["price"] = mt5.symbol_info_tick(symbol).ask
    else:
        return {"success": False, "message": "Position with this ticket not found"}
    if volume == 0 or Decimal(str(round(volume, 2))) > position_volume:
        request["volume"] = round(float(position_volume), 2)

    result = mt5.order_send(request)
    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        if Decimal(str(round(volume, 2))) < position_volume:
            return {"success": True, "message": "Position partial closed successfully", "result": result._asdict()}
        return {"success": True, "message": "Position closed successfully", "result": result._asdict()}
    elif not result:
        return {"success": False, "message": f"Check connection to metatrader"}
    else:
        return {"success": False, "message": f"Failed to close position: {result.comment}", "result": result._asdict()}
    

def close_opposite(symbol: str, volume: float, order_side: str) -> int:
    positions = get_positions() or {}
    copied_volume = Decimal(str(round(volume, 2)))
    
    
    for position in positions:
        if position['Symbol'] == symbol and position['Type'].lower() != order_side:
            if position['Volume'] <= copied_volume:
                result = close_position(symbol, position['Ticket'])
                if result:
                    copied_volume -= position['Volume']
            else:
                result = close_position(symbol, position['Ticket'], round(float(copied_volume), 2))
                if result:
                    return 0.0

    return round(float(copied_volume), 2)


def open_position(symbol: str, volume: float, order_side: str, price: float= None,  tp_price: float = None, sl_price: float = None, magic: int = 0, deviation: int = 50):
    modified_volume = close_opposite(symbol, volume, order_side)
    if modified_volume == 0:
        return {"success": True, "message": "Position done by close opposite positions"}
    if not mt5.symbol_info_tick(symbol):
        return {"success": False, "message": f"Check connection to metatrader"}


    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": modified_volume,
        "type": mt5.ORDER_TYPE_BUY,
        "price": mt5.symbol_info_tick(symbol).ask,
        "deviation": deviation,
        "magic": magic,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }

    if order_side == 'sell':
        request['type'] = mt5.ORDER_TYPE_SELL
        request['price'] = mt5.symbol_info_tick(symbol).bid
    
    if tp_price:
        request['tp'] = tp_price
    if sl_price:
        request['sl'] = sl_price
    
    if price:
        request['price'] = price
        request['type_filling'] = mt5.ORDER_FILLING_FOK
    
    
    result = mt5.order_send(request)
    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        return {"success": True, "message": "Position opened successfully", "result": result._asdict()}
    elif not result:
        return {"success": False, "message": f"Check connection to metatrader"}
    else:
        return {"success": False, "message": f"Failed to open position", "done": str(volume - modified_volume) , "result": result._asdict()}


def send_pending_order(symbol: str, volume: float, order_side: str, price: float, tp_price: float = None, sl_price: float = None, magic: int = 0, deviation: int = 50):
    request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": volume,
        "type": mt5.ORDER_TYPE_BUY_LIMIT,
        "price": price,
        "deviation": deviation,
        "magic": magic,
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN,
    }

    if order_side == 'sell':
        request['type'] = mt5.ORDER_TYPE_SELL_LIMIT
    if tp_price:
        request['tp'] = tp_price
    if sl_price:
        request['sl'] = sl_price

    result = mt5.order_send(request)
    print(result)
    if result and result.retcode == mt5.TRADE_RETCODE_DONE:
        return {"success": True, "message": "Order placed successfully", "result": result._asdict()}

    elif not result:
        return {"success": False, "message": f"Check connection to metatrader"}
    
    else:
        return {"success": False, "message": f"Failed to place the order", "result": result._asdict()}



@app.route('/init_metatrader', methods=['POST'])
def init_metatrader_endpoint():
    data = request.json  
    if not data or not all(key in data for key in ("login", "server", "password")):
        return jsonify({"error": "Missing required fields: login, server, password"}), 400

    login = data["login"]
    server = data["server"]
    password = data["password"]

    result = init_metatrader(login, server, password)
    return jsonify(result)


@app.route('/get_positions', methods=['GET'])
def get_positions_endpoint():
    positions = get_positions()
    if positions is None:
        return jsonify({"success": False, "message": "Check connection to metatrader"}), 404
    return jsonify({"success": True, "positions": positions})


@app.route('/get_aggregated', methods=['GET'])
def get_aggregated_positions_endpoint():
    aggregated_positions = get_aggregated_positions()
    if aggregated_positions is None:
        return jsonify({"success": False, "message": "Check connection to metatrader"}), 404
    return jsonify({"success": True, "aggregated_positions": aggregated_positions})


@app.route('/get_balance_info', methods=['GET'])
def get_balance_info_endpoint():
    balance_info = get_balance_info()
    if balance_info is None:
        return jsonify({"success": False, "message": "Check connection to metatrader"}), 404
    return jsonify({"success": True, "balance_info": balance_info})


@app.route('/get_orders', methods=['GET'])
def get_orders_endpoint():
    orders = get_orders()
    if orders is None:
        return jsonify({"success": False, "message": "Check connection to metatrader"}), 404
    return jsonify({"success": True, "orders": orders})


@app.route('/get_price/<symbol>', methods=['GET'])
def get_price_endpoint(symbol):
    price_info = get_price(symbol)
    if price_info is None:
        return jsonify({"success": False, "message": f"Price information for symbol '{symbol}' not found"}), 404
    return jsonify({"success": True, "price_info": price_info})


@app.route('/close_position', methods=['POST'])
def close_position_endpoint():
    data = request.json
    required_fields = ["symbol", "ticket"]

    if not data or not all(field in data for field in required_fields):
        return jsonify({"success": False, "message": f"Missing required fields: {', '.join(required_fields)}"}), 400

    symbol = data["symbol"]
    ticket = data["ticket"]
    volume = data.get("volume", 0)
    magic = data.get("magic", 0)
    deviation = data.get("deviation", 50)

    result = close_position(symbol, ticket, volume, magic, deviation)
    if result['success'] == False: 
        return jsonify(result), 404
    return jsonify(result)


@app.route('/open_position', methods=['POST'])
def open_position_endpoint():
    data = request.json
    required_fields = ["symbol", "volume", "order_side"]

    if not data or not all(field in data for field in required_fields):
        return jsonify({"success": False, "message": f"Missing required fields: {', '.join(required_fields)}"}), 400

    symbol = data["symbol"]
    volume = data["volume"]
    order_side = data["order_side"]
    price = data.get("price")
    tp_price = data.get("tp_price")
    sl_price = data.get("sl_price")
    magic = data.get("magic", 0)
    deviation = data.get("deviation", 50)

    result = open_position(symbol, volume, order_side, price, tp_price, sl_price, magic, deviation)
    if result['success'] == False: 
        return jsonify(result), 404
    return jsonify(result)


@app.route('/send_pending_order', methods=['POST'])
def send_pending_order_endpoint():
    data = request.json
    required_fields = ["symbol", "volume", "order_side", "price"]

    if not data or not all(field in data for field in required_fields):
        return jsonify({"success": False, "message": f"Missing required fields: {', '.join(required_fields)}"}), 400

    symbol = data["symbol"]
    volume = data["volume"]
    order_side = data["order_side"]
    price = data["price"]
    tp_price = data.get("tp_price")
    sl_price = data.get("sl_price")
    magic = data.get("magic", 0)
    deviation = data.get("deviation", 50)

    result = send_pending_order(symbol, volume, order_side, price, tp_price, sl_price, magic, deviation)
    if result['success'] == False: 
        return jsonify(result), 404
    return jsonify(result)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
