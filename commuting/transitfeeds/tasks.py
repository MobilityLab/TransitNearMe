import json
import logging
import urllib2

from celery.task import periodic_task
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.gis.geos import Point

from transitfeeds.models import Query, BusPosition, RailPrediction

def get_feed_data(provider_name, url_pattern):
	api_key = ()

	if provider_name in dict(settings.TRANSITFEED_API_KEYS):
		api_key = dict(settings.TRANSITFEED_API_KEYS)[provider_name]

	query_time = datetime.now()
	query = Query(provider_name=provider_name, created=query_time)
	query.save()
		
	try:
		url = url_pattern % api_key
		response = urllib2.urlopen(url_pattern % api_key)
		data = response.read()
	except Exception as ex:
		logging.error('Caught exception querying transit feed: %s' % ex)
		raise

	query.success = True
	query.save()		

	return data, query

@periodic_task(run_every=timedelta(seconds=30), ignore_result=True)
def get_WMATA_bus_locations():

	data, query = get_feed_data('WMATA', 'http://api.wmata.com/Bus.svc/json/JBusPositions?routeID=&includingVariations=true&api_key=%s')
	json_data = json.loads(data)
	
	for bus in json_data['BusPositions']:
		start = datetime.strptime(bus['TripStartTime'], '%Y-%m-%dT%H:%M:%S')
		end = datetime.strptime(bus['TripEndTime'], '%Y-%m-%dT%H:%M:%S')
		last = datetime.strptime(bus['DateTime'], '%Y-%m-%dT%H:%M:%S')
		deviation = float(bus['Deviation'])
		location = Point(float(bus['Lon']), float(bus['Lat'])) 
		
		position = BusPosition(
			query=query,
			route_id=bus['RouteID'],
			trip_id=bus['TripID'],
			vehicle_id=bus['VehicleID'],
			headsign=bus['TripHeadsign'],
			direction=int(bus['DirectionNum']),
			direction_text=bus['DirectionText'],
			trip_start_time=start,
			trip_end_time=end,
			last_report_time=last,
			deviation=deviation,
			location=location)
		position.save()

@periodic_task(run_every=timedelta(seconds=30), ignore_result=True)
def get_WMATA_rail_predictions():

	data, query = get_feed_data('WMATA', 'http://api.wmata.com/StationPrediction.svc/json/GetPrediction/All?api_key=%s')
	json_data = json.loads(data)
	
	for train in json_data['Trains']:
		prediction = RailPrediction(
			query=query,
			location_id=train['LocationCode'],
			location_name=train['LocationName'],
			group=train['Group'],
			line=train['Line'],
			destination_id=train['DestinationCode'],
			destination_name=train['Destination'],
			minutes=train['Min'],
			cars=train['Car'])
		prediction.save()
