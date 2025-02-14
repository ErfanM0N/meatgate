import requests

url = "http://127.0.0.1:5000/get_aggregated"
response = requests.get(url)

if response.status_code == 200:
    print("Succes:", response.json())
else:
    print("Error:", response.status_code, response.text)
