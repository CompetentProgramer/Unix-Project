import os
import requests
import json
import yaml

with open('servers.yaml') as f:
    servers = yaml.safe_load(f)
server_data = []
for i, data in servers.items():
    server_data.append({
        "Api_URL": data["api_url"],
        "Api_Key": data["api_key"],
    })

#Server1 Settings
API_URL1 = server_data[0]["Api_URL"]
API_KEY1 = os.environ.get("OBS_API_KEY", server_data[0]["Api_Key"])
headers1 = {
    "X-API-Key": API_KEY1
}
#Server2 Settings
API_URL2 = server_data[1]["Api_URL"]
API_KEY2 = os.environ.get("OBS_API_KEY", server_data[1]["Api_Key"])
headers2 = {
    "X-API-Key": API_KEY2
}
#Server3 settings
API_URL3 = server_data[2]["Api_URL"]
API_KEY3 = os.environ.get("OBS_API_KEY", server_data[2]["Api_Key"])
headers3 = {
    "X-API-Key": API_KEY3
}
#Server4 Settings
API_URL4 = server_data[3]["Api_URL"]
API_KEY4 = os.environ.get("OBS_API_KEY", server_data[3]["Api_Key"])
headers4 = {
    "X-API-Key": API_KEY4
}

def pollerFunc(i):
    print("pollerCalled")
    if i == 1:
        return pollerHelper(API_URL1, headers1)
    elif i == 2:
        return pollerHelper(API_URL2, headers2)
    elif i == 3:
        return pollerHelper(API_URL3, headers3)
    elif i == 4:
        return pollerHelper(API_URL4, headers4)

def pollerHelper(_apiurl, _header):
    try :
        metrics_response = requests.get(f"{_apiurl}/metrics", headers=_header , timeout=(.5,10))
        # Handle specific HTTP status codes
        if metrics_response.status_code == 200:
            return json.loads(metrics_response.text)
        elif metrics_response.status_code == 401:
            print(f"Unauthorized (401) at {_apiurl}/metrics. Check your headers/credentials.")
            return -1
        elif metrics_response.status_code == 503:
            print(f"Service Unavailable (503) at {_apiurl}/metrics. The server might be overloaded.")
            return -1
        else:
            return -1
    except requests.exceptions.ConnectTimeout:
        print(f"Timeout {_apiurl}/metrics")
        return -1
    except requests.exceptions.RequestException as e:
        print(f"Error {_apiurl}/metrics", e)
        return -1
