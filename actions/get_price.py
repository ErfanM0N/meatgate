import requests

symbol = "XAUUSD"
url = f"http://127.0.0.1:5000/get_price/{symbol}"
response = requests.get(url)

if response.status_code == 200:
    print("Price Info:", response.json())
else:
    print("Error:", response.status_code, response.text)
