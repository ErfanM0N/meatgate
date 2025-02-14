import requests

url = "http://127.0.0.1:5000/get_balance_info"
response = requests.get(url)

if response.status_code == 200:
    print("Balance Info:", response.json())
else:
    print("Error:", response.status_code, response.text)
