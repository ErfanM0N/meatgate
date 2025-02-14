import requests

url = "http://127.0.0.1:5000/open_position"
payload = {
    "symbol": "XAUUSD",
    "volume": 0.09,
    "order_side": "buy",
    "tp_price": 2400.0,
    "sl_price": 2800.0
}
response = requests.post(url, json=payload)

if response.status_code == 200:
    print("Response:", response.json())
else:
    print("Error:", response.status_code, response.text)
