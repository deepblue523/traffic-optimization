import requests
import json

def make_rest_call_post(url, payload_obj):
    payload_json = json.dumps(payload_obj)
    #print(payload_json)
    
    headers =  {'Content-Type': 'application/json; charset=utf-8'}
    return requests.post(url, data=payload_json, headers=headers)




