import os
import requests
import json

#Server1 Settings
API_URL1 = "http://<add server ip adder here>:8090"
API_KEY1 = os.environ.get("OBS_API_KEY", "Add API Key Here")
headers1 = {
    "X-API-Key": API_KEY1
}
#Server2 Settings
API_URL2 = "http://<add server ip adder here>:8090"
API_KEY2 = os.environ.get("OBS_API_KEY", "Add API Key Here")
headers2 = {
    "X-API-Key": API_KEY2
}
#Server3 settings
API_URL3 = "http://<add server ip adder here>:8090"
API_KEY3 = os.environ.get("OBS_API_KEY", "Add API Key Here")
headers3 = {
    "X-API-Key": API_KEY3
}
#Server4 Settings
API_URL4 = "http://<add server ip adder here>:8090"
API_KEY4 = os.environ.get("OBS_API_KEY", "Add API Key Here")
headers4 = {
    "X-API-Key": API_KEY4
}

def pollerFunc(i):
    print("pollerCalled")
    if i == 1:
        metrics_response = requests.get(f"{API_URL1}/metrics", headers=headers1)
    elif i == 2:
        metrics_response = requests.get(f"{API_URL2}/metrics", headers=headers2)
    elif i == 3:
        metrics_response = requests.get(f"{API_URL3}/metrics", headers=headers3)
    elif i == 4:
        metrics_response = requests.get(f"{API_URL4}/metrics", headers=headers4)
    if metrics_response.status_code == 200:
        print("Latest Metrics:", metrics_response.json())
        return json.loads(metrics_response.text)
    else:
        print(f"Error {metrics_response.status_code}:", metrics_response.json())


