import requests

API_BASE_URL = "http://127.0.0.1:8000"


def get_supplier_predictions(period="all"):
    response = requests.get(
        f"{API_BASE_URL}/supplier-predictions",
        params={"period": period},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def refresh_model():
    response = requests.post(
        f"{API_BASE_URL}/refresh-model",
        timeout=120,
    )
    response.raise_for_status()
    return response.json()