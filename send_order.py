import requests

url = "http://127.0.0.1:5000/send_pending_order"
payload = {
    "symbol": "XAUUSD",
    "volume": 0.1,
    "order_side": "buy",
    "price": 2600.0,
    "tp_price": 3000.0,
    "sl_price": 2500.0
}
response = requests.post(url, json=payload)

if response.status_code == 200:
    print("Response:", response.json())
else:
    print("Error:", response.status_code, response.text)
