import abc
import json
import urllib2

from datetime import datetime
from django.contrib.gis.geos import Point
from transitapis.apis.base import Base
from transitapis.models import Stop, Prediction

class Metrorail(Base):
    """
    API for getting information about rail service operated by WMATA.

    Refer to http://developer.wmata.com/docs for official documentation.

    To get a list of all stops:

        http://api.wmata.com/Rail.svc/json/JStations?api_key=YOUR_API_KEY

    An API call may be unsuccessful because of a bad API key or because the 
    WMATA API limits have been exceeded, in which case the return code is 
    403 Forbidden. A successful call returns status code 200 OK.

    Successful calls return JSON of the form:

        {
            "Stations": [
                {
                    "Code": "A03",
                    "Lat": 38.9095980575,
                    "LineCode1": "RD",
                    "LineCode2": null,
                    "LineCode3": null,
                    "LineCode4": null,
                    "Lon": -77.0434143597,
                    "Name": "Dupont Circle",
                    "StationTogether1": "",
                    "StationTogether2": ""
                },
                ...
            ]
        }

    Each rail station may be identified by one or more "codes", each of which
    is serviced by one or more "line codes". For example, "Metro Center"
    station, which services the Red line on one platform and the Blue and
    Orange lines on another platform, appears twice in the list. First, it
    appears with Code "A01", LineCode1 "RD", and StationTogether1 "C01".
    Later, it appears again with Code "C01", LineCode1 "BL", LineCode2 "OR",
    and StationTogether1 "A01".

    To get predicted arrival times for particular stops:

        http://api.wmata.com/StationPrediction.svc/json/GetPrediction/CODE_1,CODE_2,...?api_key=YOUR_API_KEY

    Use one or more codes as returned above as arguments to the URL.

    To get predicted arrival times for all stops:

        http://api.wmata.com/StationPrediction.svc/json/GetPrediction/All?api_key=YOUR_API_KEY

    Successful calls return JSON of the form:

        {
            "Trains": [
                {
                    "Car": "6",
                    "Destination": "Shady Gr",
                    "DestinationCode": "A15",
                    "DestinationName": "Shady Grove",
                    "Group": "2",
                    "Line": "RD",
                    "LocationCode": "A01",
                    "LocationName": "Metro Center",
                    "Min": "BRD"
                }
            ]
        }

    The "LocationCode" and "LocationName" field describe the stop that the
    prediction applies to. The "Group" field refers to the track number 
    within the stop, usually 1 or 2. The "Min" field contains either an
    integer number of minutes, "ARR" for arriving, or "BRD" for boarding.

    """
    required_options = ['key']
    base_url = 'http://api.wmata.com'

    def get_all_stops(self):
        url = '%s/Rail.svc/json/JStations?api_key=%s' % (
            self.base_url, 
            self.options['key'])

        try:
            response = urllib2.urlopen(url)
        except urllib2.HttpError:
            raise

        data = response.read()
        json_data = json.loads(data)

        stops = {}
        for station in json_data['Stations']:
            name = station['Name']
            stop = stops.get(name, None)
            if stop:
                stop.api_data += ',' + station['Code']
            else:
                stop = Stop(
                    name=name,
                    location=Point(
                        x=float(station['Lon']),
                        y=float(station['Lat']),
                        srid=4326),                
                    api_name=self.name,
                    api_data=station['Code'])
            stops[name] = stop

        return stops.values()
    
    def _get_linecodes(self, station):
        return [v for k,v in station.items() if (v and k.startswith('LineCode'))]
    
    def get_predictions(self, stop):
        if not isinstance(stop, Stop):
            raise ValueError, stop

        url = '%s/StationPrediction.svc/json/GetPrediction/%s?api_key=%s' % (
            self.base_url,
            stop.api_data,
            self.options['key'])

        try:
            query_time = datetime.now()
            response = urllib2.urlopen(url)
        except urllib2.HttpError:
            raise

        data = response.read()
        json_data = json.loads(data)
       
        predictions = []
        for train in json_data['Trains']:
            prediction = Prediction(
                retrieved=query_time,
                stop=stop,
                route=train['Line'],
                destination=train['DestinationName'],
                wait=train['Min'])
            
            if prediction.destination.upper() != 'NO PASSENGER':
	            predictions.append(prediction)

        return predictions
 
class Metrobus(Base):
    """
    API for getting information about bus service operated by WMATA.

    Refer to http://developer.wmata.com/docs for official documentation.

    To get a list of all stops:

        http://api.wmata.com/Bus.svc/json/JStops?api_key=YOUR_API_KEY

    An API call may be unsuccessful because of a bad API key or because the
    WMATA API limits have been exceeded, in which case the return code is
    403 Forbidden. A successful call returns status code 200 OK.

    Successful calls return JSON of the form:

        {
            "Stops": [
                {
                    "Lat": 38.937204,
                    "Lon": -76.993694,
                    "Name": "10TH ST + PERRY PL",
                    "Routes": [
                        "H8",
                        "H9"
                    ],
                    "StopID": "1002242"
                },
                ...
            ]
        }

    Note that there may be results in the list that appear to be duplicates
    except for their location. This is usually caused by bus stops that are
    across the street from each other and service the same routes going in
    opposite directions.

    To get predicted arrival times for a particular stop:

        http://api.wmata.com/NextBusService.svc/json/JPredictions?StopID=STOP_ID&api_key=YOUR_API_KEY

    Use a single "StopID" code as returned above as an argument to the URL.

    Successful calls return JSON of the form:

        {
            "Predictions": [
                {
                    "DirectionNum": "1",
                    "DirectionText": "East to Rhode Island Ave Station",
                    "Minutes": 3,
                    "RouteID": "H8",
                    "VehicleID": "4274"
                },
                ...
            ],
            "StopName": "10th St + Perry Pl"
        }

    The "Minutes" field is always an integer number of minutes, including
    a possible value of 0 indicating that a bus is currently at the stop.

    """
    required_options = ['key']
    base_url = 'http://api.wmata.com'

    def get_all_stops(self):
        url = '%s/Bus.svc/json/JStops?api_key=%s' % (
            self.base_url,
            self.options['key'])

        try:
            response = urllib2.urlopen(url)
        except urllib2.HttpError:
            raise

        data = response.read()
        json_data = json.loads(data)

        stops = []
        for stop in json_data['Stops']:
            stops.append(Stop(
                name=stop['Name'],
                location=Point(
                    x=float(stop['Lon']),
                    y=float(stop['Lat']),
                    srid=4326),
                api_name=self.name,
                api_data=stop['StopID']))

        return stops

    def get_predictions(self, stop):
        if not isinstance(stop, Stop):
            raise ValueError, stop

        url = '%s/NextBusService.svc/json/JPredictions?StopID=%s&api_key=%s' % (
            self.base_url,
            stop.api_data,
            self.options['key'])

        try:
            query_time = datetime.now()
            response = urllib2.urlopen(url)
        except urllib2.HttpError:
            raise

        data = response.read()
        json_data = json.loads(data)

        predictions = []
        for prediction in json_data['Predictions']:
            predictions.append(Prediction(
                retrieved=query_time,
                stop=stop,
                route=prediction['RouteID'],
                destination=prediction['DirectionText'],
                wait=prediction['Minutes']))

        return predictions 

