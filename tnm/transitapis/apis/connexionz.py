import abc
import urllib2

from datetime import datetime
from django.contrib.gis.geos import Point
from transitapis.apis.base import Base
from transitapis.models import Stop, Prediction
from xml.dom import minidom

class Connexionz(Base):
    """
    API for getting information about transit service published by Connexionz.

    To get a list of all stops:

        http://CONNEXIONZ_URL/rtt/Public/Utility/File.aspx?ContentType=SQLXML&Name=Platform.xml

     A successful call returns status code 200 OK with XML of the form:

        <?xml version="1.0"?>
        <Platforms xmlns="urn:connexionz-co-nz">
          <Content Expires="2011-12-15T03:32:00-05:00" />
          <Platform PlatformTag="83" PlatformNo="51001" Name="Ballston Metro, Fairfax Dr EB @ N Stafford St, NS" BearingToRoad="3.5508984e+002" RoadName="FAIRFAX DR">
            <Position Lat="3.888209232000000e+001" Long="-7.711087631000000e+001" />
          </Platform>
          ...
        </Platforms>

     To get predicted arrival times for a particular stop:

        http://CONNEXIONZ_URL/rtt/Public/Utility/File.aspx?contenttype=SQLXML&Name=RoutePositionET.xml&PlatformTag=PLATFORM_TAG

    Successful calls return XML of the form:

        <?xml version="1.0"?>
        <RoutePositionET xmlnx="urn:connexionz-co-nz">
          <Content Expires="2011-12-14T14:54:01-05:00" MaxArrivalScope="45" />
          <Platform PlatformTag="83" Name="Ballston Metro, Fairfax Dr, EB @ N Stafford St, NS">
            <Route RouteNo="51" Name="Ballston Metro - Virginia Hospital Center">
              <Destination Name="Lee Hwy">
                <Trip ETA="15" />
              </Destination>
            </Route>
            ...
          </Platform>
        </RoutePositionET>

    """
    required_options = ['url']
    base_path = '/rtt/public/utility/file.aspx?contenttype=SQLXML'

    def get_all_stops(self):
        url = '%s%s&Name=Platform.xml' % (
            self.options['url'],
            self.base_path)

        try:
            response = urllib2.urlopen(url)
        except urllib2.HttpError:
            raise

        dom = minidom.parse(response)

        stops = []
        for platform_elem in dom.getElementsByTagName('Platform'):
            tag = platform_elem.getAttribute('PlatformTag')
            name = platform_elem.getAttribute('Name')
            
            position_elems = platform_elem.getElementsByTagName('Position')
            if 1 != len(position_elems):
                continue

            lat = position_elems[0].getAttribute('Lat')
            lon = position_elems[0].getAttribute('Long')

            if tag and name and lat and lon:
                stops.append(Stop(
                    name=name,
                    location=Point(x=float(lon), y=float(lat), srid=4326),
                    api_id=self.id,
                    api_data=tag))

        return stops

    def get_predictions(self, stop):
        if not isinstance(stop, Stop):
            raise ValueError, stop

        url = '%s%s&Name=RoutePositionET.xml&PlatformTag=%s' % (
            self.options['url'],
            self.base_path,
            stop.api_data)

        try:
            query_time = datetime.now()
            response = urllib2.urlopen(url)
        except urllib2.HttpError:
            raise

        dom = minidom.parse(response)

        predictions = []
        for route_elem in dom.getElementsByTagName('Route'):
            route = route_elem.getAttribute('RouteNo')
            
            destination_elems = route_elem.getElementsByTagName('Destination')
            if 1 != len(destination_elems):
                continue
            
            destination = destination_elems[0].getAttribute('Name')

            trip_elems = destination_elems[0].getElementsByTagName('Trip')
            for trip_elem in trip_elems:
                eta = trip_elem.getAttribute('ETA')

                if route and destination and eta:
                    predictions.append(Prediction(
                        retrieved=query_time,
                        stop=stop,
                        route=route,
                        destination=destination,
                        wait=eta)) 

        return predictions
    
