import abc
import urllib2

from datetime import datetime
from django.contrib.gis.geos import Point
from transitapis.apis.base import Base
from transitapis.models import Stop, Prediction
from xml.dom import minidom

class NextBus(Base):
    """
    API for getting information about transit service published by NextBus.

    To get a list of all routes and stops:

        http://webservices.nextbus.com/service/publicXMLFeed?command=routeConfig&a=AGENCY_NAME

    This call always returns with a status code of 200 OK, even if the
    provided agency name is invalid.

    Unsuccessful calls due to an invalid agency name return XML of the form:

        <?xml version="1.0" encoding="utf-8" ?>
        <body copyright="...">
        <Error shouldRetry="false">
          Agency parameter a=AGENCY_NAME is not valid
        </Error>
        </body>

    Successful calls return XML of the form:

        <?xml version="1.0" encoding="utf-8" ?>
        <body copyright="...">
        <route tag="..." title="..." shortTitle="..." color="0000ff" oppositeColor="000000" latMin="38.8969499" latMax="38.91583" lonMin="-77.0679" lonMax="-77.00709">
            <stop tag="..." title="..." lat="38.89953" lon="-77.00709" stopId="0001"/>
            ...
            <direction tag="..." title="..." name="" useForUI="true">
                <stop tag="..."/>
                ...
            </direction>
            ...
            <path>
                <point lat="38.91583" lon="-77.0679"/>
                ...
            </path>
        </route>
        ...
        </body>

    Each route has a title and an abbreviated title associated with it, and
    provides color and bounding geographic information. Each stop has a title,
    an abbreviated tag, a position, and a unique stop ID. Direction and path
    information are also included along with the route data.

    To get predicted arrival times for a particular stop:

        http://webservices.nextbus.com/service/publicXMLFeed?command=predictions&a=AGENCY_NAME=stopId=STOP_ID

    Successful calls return XML of the form:

        <?xml version="1.0" encoding="utf-8" ?>
        <body copyright="...">
        <predictions agencyTitle="..." routeTitle="..." routeTag="..." stopTitle="..." stopTag="...">
        <direction title="...">
        <prediction epochTime="1323889447747" seconds="24" minutes="0" isDeparture="false" dirTag="..." vehicle="1110" block="10" />
        ...
        </direction>
        ...
        </predictions>
        </body>

    """
    required_options = ['agency_id']
    base_url = 'http://webservices.nextbus.com/service/publicXMLFeed'
    
    def get_all_stops(self):
        url = '%s?command=routeConfig&a=%s' % (
            self.base_url,
            self.options['agency_id'])

        try:
            response = urllib2.urlopen(url)
        except urllib2.HttpError:
            raise

        dom = minidom.parse(response)
        
        stops = []
        for stop_elem in dom.getElementsByTagName('stop'):
            title = stop_elem.getAttribute('title')
            lon = stop_elem.getAttribute('lon')
            lat = stop_elem.getAttribute('lat')
            stopId = stop_elem.getAttribute('stopId')

            if title and lon and lat and stopId:
                stops.append(Stop(
                    name=title,
                    location=Point(x=float(lon), y=float(lat), srid=4326),
                    api_name=self.name,
                    api_data=stopId))

        return stops
                
    def get_predictions(self, stop):
        if not isinstance(stop, Stop):
            raise ValueError, stop

        url = '%s?command=predictions&a=%s&stopId=%s' % (
            self.base_url,
            self.options['agency_id'],
            stop.api_data)

        try:
            query_time = datetime.now()
            response = urllib2.urlopen(url)
        except urllib2.HttpError:
            raise

        dom = minidom.parse(response)
        
        predictions = []
        for route_elem in dom.getElementsByTagName('predictions'):
            route = route_elem.getAttribute('routeTitle')

            for dir_elem in route_elem.getElementsByTagName('direction'):
                direction = dir_elem.getAttribute('title')

                for pred_elem in dir_elem.getElementsByTagName('prediction'):
                    minutes = pred_elem.getAttribute('minutes')

                    if route and direction and minutes:
                        predictions.append(Prediction(
                            retrieved=query_time,
                            stop=stop,
                            route=route,
                            destination=direction,
                            wait=minutes))

        return predictions

