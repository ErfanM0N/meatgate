import requests

url = "http://127.0.0.1:5000/init_metatrader"
payload = {"login": 88825134, "server": "MetaQuotes-Demo", "password": "Z_WdKwN3"}
response = requests.post(url, json=payload)
print(response.json())
