import requests
import json

fedex_url="https://apis-sandbox.fedex.com/"

def authenticate():
    url = fedex_url+"oauth/token"

    input={
        'grant_type':'client_credentials',
        'client_id':'l71845f33ec3b24082a32c651af161c216',
        'client_secret':'d905ec8acdf646269ef8ef3c66260090'
    }
    payload = input # 'input' refers to JSON Payload
    headers = {
        'Content-Type': "application/x-www-form-urlencoded"
        }

    response = requests.request("POST", url, data=payload, headers=headers)

    response_dict=json.loads(response.text)
    return response_dict['access_token']


def validate_address(streetLines,city,state,postalcode,countrycode):
    access_token=authenticate()
    
    url = fedex_url+"address/v1/addresses/resolve"

    address_input={'addressesToValidate':[
            {
                    'address':{
                    'streetLines':[''+streetLines+''],
                    'city':''+city+'',
                    'stateOrProvinceCode':''+state+'',
                    'postalCode':''+postalcode+'',
                    'countryCode':''+countrycode+''
                }
            }
        ]}

  
    payload = json.dumps(address_input) # 'input' refers to JSON Payload
    headers = {
        'x-customer-transaction-id':'123',
        'Content-Type': "application/json",
        'X-locale': "en_US",
        'Authorization': 'Bearer '+access_token
        }

    response = requests.request("POST", url, data=payload, headers=headers)

    response_dict=json.loads(response.text)
    #find if any error in response before reading
    if 'errors' in response_dict:
        return response_dict['errors'][0]['message']
        
    else:
        #check if any resolved addresses are returned
        if response_dict['output']['resolvedAddresses']:
            add_dict=response_dict['output']['resolvedAddresses'][0]
            #check if any problem in address
            if len(add_dict['customerMessages'])>0:
               
                return str(add_dict['customerMessages'][0]['message'])
            else:
                
                return "valid"

def location_check(streetLines,city,state,postalcode,countrycode,distance):
    access_token=authenticate()
    
    url = fedex_url+"location/v1/locations"

    
    location_payload={
        'locationsSummaryRequestControlParameters' :
        {
            'distance':{
                'units':'MI',
                'value':'4'
            },
            'maxResults':'5',
            'customerTranscationId':'DroneID'
        },
        'location':
        {
            'address':{
                    'streetLines':[''+streetLines+''],
                    'city':''+city+'',
                    'stateOrProvinceCode':''+state+'',
                    'postalCode':''+postalcode+'',
                    'countryCode':''+countrycode+''
            }
        }
    }
    payload = json.dumps(location_payload) # 'input' refers to JSON Payload
    headers = {
        'x-customer-transaction-id':'123',
        'Content-Type': "application/json",
        'X-locale': "en_US",
        'Authorization': 'Bearer '+access_token
        }

    response = requests.request("POST", url, data=payload, headers=headers)

    response_dict=json.loads(response.text)
    # print(response_dict)

def service_availability(sender,receiver):
    access_token=authenticate()
    
    url = fedex_url+"availability/v1/packageandserviceoptions/"

    
    requestshipment={
        'requestedShipment' :
        {
            'shipper':{
                'address':
           {
                   'streetLines':[''+str(sender['street'])+''],
                    'city':''+sender['city']+'',
                    'stateOrProvinceCode':''+sender['stateorprovince']+'',
                    'postalCode':''+sender['postalcode']+'',
                    'countryCode':''+sender['countrycode']+''
            }
            },
            'recipients':[{
               'address':
           {
                    'streetLines':[''+str(receiver['street'])+''],
                    'city':''+receiver['city']+'',
                    'stateOrProvinceCode':''+receiver['stateorprovince']+'',
                    'postalCode':''+receiver['postalcode']+'',
                    'countryCode':''+receiver['countrycode']+''
            }
            }]
        }
    }
  
    payload = json.dumps(requestshipment) # 'input' refers to JSON Payload
    headers = {
        'x-customer-transaction-id':'123',
        'Content-Type': "application/json",
        'X-locale': "en_US",
        'Authorization': 'Bearer '+access_token
        }

    response = requests.request("POST", url, data=payload, headers=headers)
    priority_options=0
    response_dict=json.loads(response.text)
    if 'output' in response_dict:
        all_options=response_dict['output']['packageOptions']
        for items in all_options:
            if items['serviceType']['key']=='FEDEX_FREIGHT_PRIORITY':
                priority_options+=1
        

   
    return priority_options
 