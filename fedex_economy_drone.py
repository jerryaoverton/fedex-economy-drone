import os
from time import sleep
import socketio
import requests
from flask import Flask, render_template
import uuid

app = Flask(__name__)


# define the state of the drone


ctx = {'drone_id':'',
       'drone_started': False,
       'next_action': None,
       'current_job': '',
       'max_total_jobs': 10,
       'max_consecutive_jobs': 3,
       'total_jobs': 0,
       'total_wait_cycles': 0,
       'max_wait_cycles': 10,
       'jobs_since_maintenance': 0,
       'current_battery_usage':0,
       'current_fexcoins':0}


profile={'first_name': 'Drone',
                            'last_name': '',
                            'RegistrationType': 'Drone Service',
                            'email':'',
                            'BusinessType':'',
                            'Address': '3600 Lancaster Avenue, Philadelphia, 19104',
                            'area_code': '267',
                            'phone': '897897987',
                            'image_url': 'www.pic.com/profile.jpg',
                            'profile_url': 'https://fedex-economy-drone.herokuapp.com/Drone_Info',
                            'description': 'A very useful drone',
                            'tags': 'drone, delivery',
                            'rating': 4,
                            'status': 'idle',
                            'properties':'type:Quadcopter, capacity:2kgs, flyduration:10mins'
                   }



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

    if end_of_life or idle_too_long:
        return retire
    elif hired:
        return work
    else:
        return wait


def work():
    print('working')
    ctx['jobs_since_maintenance'] += 1
    ctx['total_jobs'] += 1

    profile['status'] = 'working'
    update_profile()

    sleep(10)
    # TODO: update the order status
    ctx['current_job'] = ''

    jobs_since_maintenance = ctx['jobs_since_maintenance']
    max_consecutive_jobs = ctx['max_consecutive_jobs']
    if jobs_since_maintenance < max_consecutive_jobs:
        return wait
    else:
        return get_maintenance


def get_maintenance():
    print('getting maintenance')
    profile['status'] = 'under maintenance'
    update_profile()

    ctx['jobs_since_maintenance'] = 0
    sleep(10)
    return pay_for_maintenance


def pay_for_maintenance():
    print('paying for maintenance')
    profile['status'] = 'paying for maintenance'
    update_profile()
    sleep(10)
    return wait


def retire():
    print('retiring')
    profile['status'] = 'retired'
    update_profile()
    print("drone is retired")

    return None


def register_drone():
    print('registering drone')
    svc = '/register_user'
    drone_id='drone-'+str(uuid.uuid1())
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
    
    return render_template('index.html', msg=status_msg[ctx['next_action']],drone_id=ctx['drone_id'])

@app.route('/Drone_Info')
def drone_home():
    return render_template('Drone.html')


@sio.on('message', namespace='/order')
def on_message(order):
    print('looking for work')
    # choose a job
    # TODO: pick a job based on it's status
    if "drone" in order:
        ctx['current_job'] = order


if __name__ == '__main__':
    app.run(debug=True, port=5001)
