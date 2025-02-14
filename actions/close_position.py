import requests

url = "http://127.0.0.1:5000/close_position"
payload = {
    "symbol": "XAUUSD",
    "ticket": 3159545919,
    "volume": 0.01
}
response = requests.post(url, json=payload)

if response.status_code == 200:
    print("Response:", response.json())
else:
    print("Error:", response.status_code, response.text)
