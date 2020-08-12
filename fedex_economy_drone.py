import os
from time import sleep
import socketio
import requests
from flask import Flask, render_template
import uuid
import ast
from random import randint
import json
import datetime
import fedex_api
app = Flask(__name__)


# define the state of the drone


ctx = {'drone_id':'',
       'drone_started': False,
       'next_action': None,
       'current_job': '',
       'max_total_jobs': 100,
       'max_consecutive_jobs': 3,
       'total_jobs': 0,
       'total_wait_cycles': 0,
       'max_wait_cycles': 100,
       'jobs_since_maintenance': 0,
       'current_battery_usage':0,
       'current_fexcoins':0,
       'max_weight':5}


profile={'first_name': 'Drone',
                            'last_name': '',
                            'RegistrationType': 'Drone Service',
                            'email':'',
                            'BusinessType':'',
                            'street': '3600 Lancaster Avenue',
                            'city':'Philadelphia',
                            'stateorprovince':'PA',
                            'postalcode':'19104',
                            'countrycode':'US',
                            'area_code': '267',
                            'phone': '897897987',
                            'image_url': 'www.pic.com/profile.jpg',
                            'profile_url': 'https://fedex-economy-drone.herokuapp.com/Drone_Info',
                            'description': 'A very useful drone',
                            'tags': 'drone, delivery',
                            'rating': 4,
                            'status': 'idle',
                            'properties':'type:Quadcopter,capacity_lbs:'+str(randint(3,5))+',flyduration_min:10'
                   }

serviceproviders=[]

orders=[]
# define how the drone behaves


def wait():
    print('waiting')
    profile['status'] = 'waiting'
    ctx['total_wait_cycles'] += 1

    update_profile()
    sleep(10)

    end_of_life = ctx['total_jobs'] >= ctx['max_total_jobs']
    hired = not (ctx['current_job'] == '')
    idle_too_long = ctx['total_wait_cycles'] >= ctx['max_wait_cycles']

    # commenting retire to test maintenance
    if end_of_life or idle_too_long:
        return retire
    elif hired:
        return work
    # if hired:
    #     return work
    else:
        return wait


def work():
    
    print('working')
    
    
    ctx['total_jobs'] += 1

    profile['status'] = 'working'
    update_profile()
  
    sleep(10)
   
    order_dict=ast.literal_eval(ctx['current_job'])
    
    order_dict['status']='complete'
    update_order(str(order_dict))

    #complete the task and get payment from supplier- as customer is being charged by business
    drone_receive_payment(order_dict['supplier'],order_dict['price'])

    ctx['current_job'] = ''
    ctx['jobs_since_maintenance'] += 1
    jobs_since_maintenance = ctx['jobs_since_maintenance']
    max_consecutive_jobs = ctx['max_consecutive_jobs']
    if jobs_since_maintenance < max_consecutive_jobs:
        return wait
    else:
        return get_maintenance


def get_maintenance():
    #check the balance to decide best service provider
    get_balance()
   
    print('getting maintenance')
    #find list of service providers
    get_all_service_providers()

    if len(serviceproviders)>0: 
        nearest_fedex=find_nearest_fedEx_location()
        provider=get_best_provider()
        profile['status'] = 'under maintenance'
        update_profile()
        unique_order_id=uuid.uuid1()
        print(unique_order_id)
        order_for_service = {
                            'order_id':str(unique_order_id),
                            'supplier': provider['first_name'],
                            'customer': ctx['drone_id'],
                            'payment_method': 'tokens',
                            'price': provider['ServiceFee'],
                            'delivery_provider': 'ServiceProvider',
                            'order_details': 'Meet drone at delivery address for maintenance',
                            'delivery_address':str(nearest_fedex),
                            'terms_and_conditions': 'must not harm drone',
                            'status': 'active',
                            'status_date': '08/06/2020'
                            }
        update_order(order_for_service)
        # ctx['jobs_since_maintenance'] = 0
        sleep(10)
        return check_if_maintenance_completed
    else:
         print('No service provider for maintenance in budget')
         ctx['jobs_since_maintenance']=0
         sleep(10)
         return wait

def get_all_service_providers():
    print('get service providers')
    svc = '/list_users'
    url = smart_contract + svc
    users = requests.get(url).content
    array_users=eval(users)
    
    for user in array_users:
       for key,value in user.items():
            if key=='profile':
                try:
                    if value['RegistrationType']=='ServiceProvider' and value['ServiceType']=='DroneMaintenance':
                        serviceproviders.append(value)
                except Exception as e:
                        continue
                #  print('exception is '+ str(e.with_traceback))
    return serviceproviders
    # print(serviceproviders)

def get_best_provider():
  
    #compare the costs between service providers to find best provider
    cost=serviceproviders[0]['ServiceFee']
    print(cost+"is best")
    best_provider=serviceproviders[0]
    for provider in serviceproviders:
        if cost< provider['ServiceFee'] and ctx['current_fexcoins']>=provider['ServiceFee']:
            best_provider=provider
    
    return best_provider

def find_nearest_fedEx_location():
    #find fedex location nearest to drone to go there for service. so just need 1 nearest location
    sender_address= {'street':profile['street'],
                            'city':profile['city'],
                            'stateorprovince':profile['stateorprovince'],
                            'postalcode':profile['postalcode'],
                            'countrycode':profile['countrycode']
            }
    nearest_fedex_office=fedex_api.location_check(sender_address,1)
    return nearest_fedex_office

def get_balance():
    print('get drone balance')
    svc = '/user_balance'
    params = '?user_id='+ctx['drone_id']
    url = smart_contract + svc + params
    _msg = requests.get(url).content
    ctx['current_fexcoins']=int(_msg)

def get_user_profile(user_id):
    svc = '/user_profile'
    params = '?user_id='+user_id
    url = smart_contract + svc + params
    profile = requests.get(url).content
    return profile

def pay_for_maintenance(receiver,amount):
    print('paying for maintenance')
    profile['status'] = 'paying for maintenance'
    drone_send_payment(receiver,amount)
    update_profile()
    # ctx['next_action'] = wait
    ctx['jobs_since_maintenance'] = 0
    sleep(10)
    return wait

def check_if_maintenance_completed():
    while profile['status']!='paying for maintenance':
        ctx['next_action']='getting maintenance'
        sleep(10)
    
    return wait

def retire():
    print('retiring')
    get_balance()
    drone_send_payment('fedex',str(ctx['current_fexcoins']))
    profile['status'] = 'retired'
    update_profile()
    print("drone is retired")

    return None


def register_drone():
    print('registering drone')
    svc = '/register_user'
    # drone_id='drone-'+str(uuid.uuid1())
    drone_id='drone-fedex-economy'
    params = '?user_id='+drone_id
    url = smart_contract + svc + params
    _msg = requests.get(url).content
    ctx['drone_id']=drone_id

def drone_receive_payment(sender,amount):
    print('receving payment')
    svc = '/pay'
    params = '?sender='+sender+'&receiver='+ctx['drone_id']+'&amount='+amount
    url = smart_contract + svc + params
    _msg = requests.get(url).content
    # ctx['current_fexcoins']+=amount

def drone_send_payment(receiver,amount):
    print('sending payment')
    svc = '/pay'
    params = '?sender='+ctx['drone_id']+'&receiver='+receiver+'&amount='+amount
    url = smart_contract + svc + params
    _msg = requests.get(url).content
    ctx['drone_started'] = True

def update_profile():
    print('updating drone profile')
    svc = '/update_profile'
    params = '?user_id='+ctx['drone_id']+'&profile=' + str(profile)
    url = smart_contract + svc + params
    _msg = requests.get(url).content


def update_order(order):
    print('updating drone order')
    svc = '/update_order'
    params = '?order=' + str(order)
    url = smart_contract + svc + params
    _msg = requests.get(url).content


# connect the drone and begin operation


sio = socketio.Client()
smart_contract = os.environ['SMART_CONTRACT']
sio.connect(smart_contract, namespaces=['/profile', '/order'])

ctx['next_action'] = wait

status_msg = {wait: 'waiting',
              work: 'working',
              get_maintenance: 'getting maintenance',
              pay_for_maintenance: 'paying for maintenance',
              retire: 'retiring drone',
              register_drone: 'registering_drone',
              update_profile: 'updating profile',
              update_order: 'updating order',
              None: 'drone is out of service'
              }


@app.route('/')
def home():
    
                  
    if not ctx['drone_started']:
        register_drone()
        drone_receive_payment('fedex','100')
        ctx['drone_started'] = True

    if not ctx['next_action'] is None:
        ctx['next_action'] = ctx['next_action']()
    
    return render_template('index.html', msg=ctx['next_action'],drone_id=ctx['drone_id'])

@app.route('/Drone_Info')
def drone_home():
    return render_template('Drone.html')


@sio.on('message', namespace='/order')
def on_message(order):
    
     print('looking for work / maintenance update'+profile['status'])
     try:
        
        
        if profile['status']=='under maintenance':
            print('when in maintenance')
         
            order_dict=ast.literal_eval(order)
            
     
            #TODO check if order has any service provider drone maintenance related information
            if order_dict['status']=='complete' and order_dict['customer']==ctx['drone_id']:
                    return pay_for_maintenance(order_dict['supplier'],order_dict['price'])
        

        else:
            # print('success')
            order_dict=ast.literal_eval(order)
            order_details=dict(s.split(':') for s in order_dict['order_details'].split(','))
            profile_properties=dict(s.split(':') for s in profile['properties'].split(','))
            
            #API 1 -Address Validation
            #Check if customer address is valid for delivery
            
            customer=get_user_profile(order_dict['customer'])
            customer_profile=json.loads(customer)
            address_check=fedex_api.validate_address(customer_profile['street'],customer_profile['city'],customer_profile['stateorprovince'],customer_profile['postalcode'],customer_profile['countrycode'])
            # print(address_check)
            #only process if order is not invalid
            if address_check!= 'valid' and order_dict['status']!='Invalid Address':
                order_dict['status']='Invalid Address'
                update_order(str(order_dict))
           
            # pick up a job only when the priority shipping option available in that location
            sender_address= {'street':profile['street'],
                            'city':profile['city'],
                            'stateorprovince':profile['stateorprovince'],
                            'postalcode':profile['postalcode'],
                            'countrycode':profile['countrycode']
            }
            
            recipient_address= {'street': customer_profile['street'],
                            'city':customer_profile['city'],
                            'stateorprovince':customer_profile['stateorprovince'],
                            'postalcode':customer_profile['postalcode'],
                            'countrycode':customer_profile['countrycode']
            }
            serve_from_my_location=fedex_api.service_availability(sender_address,recipient_address)


            if serve_from_my_location>0 and profile['status']!='under maintenance' and profile['status']!='retired' and order_dict['delivery_provider'].upper()=='DRONE' and order_dict['status']=='active' and float(order_details['shipment_weight'])<=float(profile_properties['capacity_lbs']) :
                ctx['current_job'] = order
                order_dict['status']='processing'
                update_order(str(order_dict))
            elif float(order_details['shipment_weight'])>ctx['max_weight'] and order_dict['status']!='operational_error':
                order_dict['status']='operational_error'
                update_order(str(order_dict))
     except Exception as e:
        print('exception happpened due to ' +str(e.with_traceback))
if __name__ == '__main__':
    app.run(debug=True, port=5001)

