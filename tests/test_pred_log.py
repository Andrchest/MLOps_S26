import requests

url = "http://127.0.0.1:8000/predict"

payload = {
    "age": 35,
    "monthly_spend": 5000.0,
    "tenure_months": 12
}

response = requests.post(url, json=payload)
print(response.json())