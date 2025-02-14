import requests

url = "http://127.0.0.1:5000/get_orders"
response = requests.get(url)

if response.status_code == 200:
    print("Orders Info:", response.json())
else:
    print("Error:", response.status_code, response.text)
