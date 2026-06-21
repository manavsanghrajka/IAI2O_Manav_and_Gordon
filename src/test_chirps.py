import requests
import json

url = "https://climateserv.servirglobal.net/api/submitDataRequest/"
geom = {
    "type": "Polygon",
    "coordinates": [[[15.2, -4.4], [15.4, -4.4], [15.4, -4.2], [15.2, -4.2], [15.2, -4.4]]]
}

params = {
    "datatype": 0, # CHIRPS
    "begintime": "01/01/2000",
    "endtime": "12/31/2024",
    "intervaltype": 1, # monthly (usually 1, daily is 0)
    "operationtype": 5, # average
    "geometry": json.dumps(geom)
}

try:
    resp = requests.get(url, params=params)
    print(resp.json())
except Exception as e:
    print(e)
