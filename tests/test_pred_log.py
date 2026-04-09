import requests


def run_test():
    url = "http://127.0.0.1:8000/predict"
    payload = {"age": 35, "monthly_spend": 5000.0, "tenure_months": 12}

    try:
        response = requests.post(url, json=payload)
        print(response.json())
    except requests.exceptions.ConnectionError:
        print("Error: The server at http://127.0.0.1:8000 is not running.")


if __name__ == "__main__":
    run_test()
