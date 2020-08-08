import os
from time import sleep
import socketio
import requests
from flask import Flask

app = Flask(__name__)

ctx = {'current_job': '',
       'max_total_jobs': 10,
       'max_consecutive_jobs': 3,
       'total_jobs': 0,
       'total_wait_cycles': 0,
       'max_wait_cycles': 10,
       'jobs_since_maintenance': 0}

sio = socketio.Client()

smart_contract = os.environ['SMART_CONTRACT']
sio.connect(smart_contract, namespaces=['/profile', '/order'])

profile = {'image_url': 'www.pic.com/drone.jpg',
           'profile_url': 'www.mydroneprofile.com',
           'description': 'A very useful drone',
           'tags': 'drone, delivery',
           'rating': 4,
           'status': 'idle'
           }
fedex_token_network = 'http://127.0.0.1:5000/'

@app.route('/')
def home():
    register_drone()
    wait()
    return "drone is running"

def register_drone():
    print('registering drone')
    svc = '/register_user'
    params = '?user_id=drone'
    url = fedex_token_network + svc + params
    _msg = requests.get(url).content


def update_profile():
    print('updating drone profile')
    svc = '/update_profile'
    params = '?user_id=drone&profile=' + str(profile)
    url = fedex_token_network + svc + params
    _msg = requests.get(url).content


def update_order(order):
    print('updating drone order')
    svc = '/update_order'
    params = '?order=' + str(order)
    url = fedex_token_network + svc + params
    _msg = requests.get(url).content


@sio.on('message', namespace='/order')
def on_message(order):
    print('looking for work')
    # choose a job
    # TODO: pick a job based on it's status
    if "drone" in order:
        ctx['current_job'] = order


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
        retire()
    elif hired:
        work()
    else:
        wait()


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
        wait()
    else:
        get_maintenance()


def get_maintenance():
    print('getting maintenance')
    profile['status'] = 'under maintenance'
    update_profile()

    ctx['jobs_since_maintenance'] = 0
    sleep(10)
    pay_for_maintenance()


def pay_for_maintenance():
    print('paying for maintenance')
    profile['status'] = 'paying for maintenance'
    update_profile()
    sleep(10)
    wait()


def retire():
    print('retiring')
    profile['status'] = 'retired'
    update_profile()
    print("drone is retired")


if __name__ == '__main__':
    app.run(debug=True, port=5001)
