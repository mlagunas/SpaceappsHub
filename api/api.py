from bottle import route, request, run
from pymongo import MongoClient
from bson.json_util import dumps
import requests
from datetime import datetime


# Mongo configuration
mongo_ip = "40.68.44.128"
mongo_port = "27017"
mongo_client = MongoClient(
    "mongodb://" + mongo_ip + ":" + mongo_port + "")
API_CODE = "570b33d8c0275b0e221296d7b6190032"


def hazards(latitude, longitude):

    r = requests.get('http://api.openweathermap.org/data/2.5/station/find?cnt=1&lat=' +
                     str(round(latitude, 1)) + '&lon=' + str(round(longitude, 1)) +
                     '&appid=' + API_CODE)
    r = r.json()[0]
    latitude = float('%.1f' % (r['station']['coord']['lat']))
    longitude = float('%.1f' % (r['station']['coord']['lon']))

    r = requests.get('http://api.openweathermap.org/data/2.5/weather?lat=' +
                     str(round(latitude, 1)) + '&lon=' + str(round(longitude, 1)) +
                     '&appid=' + API_CODE + '&units=metric')
    r = r.json()
    try:
        temp = r['main']['temp'] or None
    except Exception:
        temp = None
    try:
        humidity = r['main']['humidity'] or None
    except Exception:
        humidity = None

    r = requests.get('http://api.openweathermap.org/data/2.5/pollution/v1/o3/' +
                     str(round(latitude, 1)) + '&lon=' + str(round(longitude, 1)) +
                     "/current.json?appid=" + API_CODE)

    r = requests.get('http://api.openweathermap.org/pollution/v1/o3/' +
                     str(round(latitude, 1)) + ',' + str(round(longitude, 1)) +
                     "/current.json?appid=" + API_CODE)
    r = r.json()
    try:
        o3 = r['data'] or None
    except Exception:
        o3 = None

    r = requests.get('http://api.openweathermap.org/pollution/v1/no2/' +
                     str(round(latitude, 1)) + ',' + str(round(longitude, 1)) +
                     '/current.json?appid=' + API_CODE)

    r = r.json()
    try:
        no2 = r['data']['no2']['value'] or None
    except Exception:
        no2 = None

    r = requests.get('http://api.openweathermap.org/pollution/v1/so2/' +
                     str(round(latitude, 1)) + ',' + str(round(longitude, 1)) +
                     '/current.json?appid=' + API_CODE)

    r = r.json()
    try:
        so2 = r['data'][0]['value'] or None
    except Exception:
        so2 = None

    return temp, humidity, o3, no2, so2, latitude, longitude


@route('/risk_value', method='GET')
def risk_value():
    latitude = float(request.query.latitude)
    longitude = float(request.query.longitude)
    return risk_value_local(latitude, longitude)


def risk_value_local(latitude, longitude):
    humidity, temp, o3, no2, so2, latitude, longitude = hazards(
        latitude, longitude)
    out = 0
    if humidity is not None:
        if humidity > 65:
            out += 2
        elif humidity > 40:
            out += 1
    if temp is not None:
        if temp < -5:
            out += 2
        elif temp < 5:
            out += 1
    if o3 is not None:
        if o3 > 360:
            out += 2
        elif o3 > 300:
            out += 1
    if no2 is not None:
        if no2 > 5.25E15:
            out += 2
        elif no2 > 2.25E15:
            out += 1
    if so2 is not None:
        if so2 > 1:
            out += 2
        elif so2 > 0:
            out += 1

    return {'value': out, 'latitude': latitude, 'longitude': longitude,
            'humidity': humidity, 'temp': temp, 'o3': o3,
            'no2': no2, 'so2': so2}


@route('/test', method='GET')
def test():
    return "Funciona!!!!!!!!!!"


@route('/authentication', method='POST')
def authentication():
    username = request.query.username
    password = request.query.password
    out = mongo_client.spaceapps.cuentas.find({"usuario": username})
    user = [o for o in out]
    print user
    if len(user) == 0:
        return "No te conozco"
    elif user[0]['password'] in password:
        return "Login OK"
    else:
        return "password incorrecto"


@route('/register', method='POST')
def register():
    username = request.query.username or None
    if username is None:
        username = request.forms.get("username")
    password = request.query.password or None
    if password is None:
        password = request.forms.get("password")
    mongo_client.spaceapps.cuentas.insert(
        {"usuario": username, "password": password})


@route('/query_all_symptons', method='GET')
def get_data():
    cursor = mongo_client.spaceapps.sintomas.find()
    return dumps(cursor)


@route('/close_users', method='GET')
def close_users():
    latitude = float(request.query.latitude)
    longitude = float(request.query.longitude)
    radius = int(round(float(request.query.radius)))
    search = {'loc': {'$near': {
        'type': "Point",
        'coordinates': [latitude, longitude],
        '$maxDistance': radius}
    }}
    cursor = mongo_client.spaceapps.sintomas.find(search)
    out = dumps(cursor)
    print out
    return out


@route('/insert_syntom', method='POST')
def insert_syntom():

    latitude = float(request.query.lat)
    longitude = float(request.query.long)
    user = str(request.query.user)
    cough = str(request.query.cough)
    sneeze = str(request.query.sneeze)
    nasal = str(request.query.nasal)
    eyes = str(request.query.eyes)
    breath = str(request.query.breath)
    wheeze = str(request.query.wheeze)
    mouth = str(request.query.mouth)

    print user
    print latitude
    print eyes

    humidity, temp, o3, no2, so2, _, _ = hazards(latitude, longitude)

    risk = risk_value_local(latitude, longitude)

    insert = {'user': user, 'date': datetime.now(), 'cough': cough,
              'loc': {'type': 'Point', 'coordinates': [longitude, latitude]},
              'sneeze': sneeze, 'nasal': nasal, 'eyes': eyes,
              'breath': breath, 'wheeze': wheeze, 'mouth': mouth,
              'humidity': humidity, 'temp': temp, 'o3': o3,
              'no2': no2, 'so2': so2, 'risk': risk}
    print insert
    mongo_client.spaceapps.sintomas.insert(insert)
    return "OK"


def main():
    run(host='0.0.0.0', port=8080)


if __name__ == "__main__":
    main()
