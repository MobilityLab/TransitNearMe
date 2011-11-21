from optparse import make_option

from django.db import connection
from django.core.management.base import NoArgsCommand, CommandError

from api import models as api_models

def dictfetchall(cursor):
	"""Returns all rows from a cursor as a dict."""
	desc = cursor.description
	return [
		dict(zip([col[0] for col in desc], row))
		for row in cursor.fetchall()
	]	

class Command(NoArgsCommand):
	option_list = NoArgsCommand.option_list + (
		make_option('--nowarning',
			action='store_false', dest='warning', default=True,
			help="Don't prompt the user with a warning about erasing data."),
		make_option('-n', '--dry-run',
			action='store_true', dest='dry_run', default=False,
			help="Do everything except modify the database."),
		make_option('--noagencies',
			action='store_false', dest='do_agencies', default=True,
			help="Don't process agencies table."),
		make_option('--nostops',
			action='store_false', dest='do_stops', default=True,
			help="Don't process stops table."),
		make_option('--noroutes',
			action='store_false', dest='do_routes', default=True,
			help="Don't process routes tables."),
	)
	help = "Imports GTFSDB data models to API database."

	def handle_noargs(self, **options):
		self.warning = options['warning']
		self.dry_run = options['dry_run']
		self.do_agencies = options['do_agencies']
		self.do_stops = options['do_stops']
		self.do_routes = options['do_routes']

		if self.warning:
			# Warn the user about erasing existing data.
			confirm = raw_input(u"""
You have requested to import GTFSDB data models into the API database.

This will erase all existing API database models.
Are you sure you want to do this?

Type 'yes' to continue, or 'no' to cancel: """)
			
			if confirm != 'yes':
				raise CommandError("Importing GTFSDB data models cancelled.")

		if self.do_agencies:
			self.process_agencies()

		if self.do_stops:
			self.process_stops()

		if self.do_routes:
			self.process_routes()

		self.stdout.write("Successfully converted GTFS models.\n")		
		if self.dry_run:
			self.stdout.write("This was just a dry run!\n")

	def process_agencies(self):
		if not self.dry_run:
			# Clear out existing DB tables.
			api_models.Agency.objects.all().delete()
	
		cursor = connection.cursor()
		cursor.execute("SELECT * FROM agency")
		gtfs_agencies = dictfetchall(cursor)
		for idx, gtfs_agency in enumerate(gtfs_agencies):
			self.stdout.write("Converting agency %d/%d '%s'.\n" % (idx + 1, len(gtfs_agencies), gtfs_agency['agency_name']))
				
			agency = api_models.Agency(
				id=int(gtfs_agency['id']),
				name=gtfs_agency['agency_name'])
			
			if not self.dry_run:
				agency.save()

	def process_stops(self):
		if not self.dry_run:
			# Clear out existing DB tables.
			api_models.Stop.objects.all().delete()
		
		# Read in stop information.
		cursor = connection.cursor()
		cursor.execute("SELECT * FROM stops")
		gtfs_stops = dictfetchall(cursor)
		for idx, gtfs_stop in enumerate(gtfs_stops):
			self.stdout.write("Converting stop %d/%d '%s'.\n" % (idx + 1, len(gtfs_stops), gtfs_stop['stop_name']))

			api_stop = api_models.Stop(
				id=int(gtfs_stop['stop_id']),
				name=gtfs_stop['stop_name'],
				geom=gtfs_stop['geom'])
			
			if not self.dry_run:
				api_stop.save()

	def process_routes(self):
		if not self.dry_run:
			# Clear out existing DB tables.
			api_models.Route.objects.all().delete()
			api_models.Pattern.objects.all().delete()
			api_models.PatternStop.objects.all().delete()
		
		# Read in pattern information.
		cursor = connection.cursor()		
		cursor.execute("SELECT * FROM routes")
		gtfs_routes = dictfetchall(cursor)
		
		for idx, gtfs_route in enumerate(gtfs_routes):
			self.stdout.write("Converting route %d/%d '%s'.\n" % (idx + 1, len(gtfs_routes), gtfs_route['route_short_name']))

			name = gtfs_route['route_short_name']
			if not name:
				name = gtfs_route['route_long_name']
			api_route = api_models.Route(
				id=int(gtfs_route['route_id']),
				agency=api_models.Agency.objects.get(id=int(gtfs_route['agency_id'])),
				name=name,
				route_type=gtfs_route['route_type'],
				color=gtfs_route['route_color'])
	
			if not self.dry_run:
				api_route.save()

			cursor.execute("SELECT array_agg(unique_patterns.trip_id), unique_patterns.stop_ids, unique_patterns.shape_dist_traveleds FROM (SELECT patterns.trip_id, array_agg(patterns.stop_id) AS stop_ids, array_agg(patterns.shape_dist_traveled) AS shape_dist_traveleds FROM (SELECT trips.trip_id, stops.stop_id, stop_times.stop_sequence, stop_times.shape_dist_traveled FROM stop_times JOIN stops ON stop_times.stop_id = stops.stop_id JOIN trips ON stop_times.trip_id = trips.trip_id WHERE trips.route_id = '%s' ORDER BY trips.trip_id, stop_times.stop_sequence) AS patterns GROUP BY patterns.trip_id) AS unique_patterns GROUP BY unique_patterns.stop_ids, unique_patterns.shape_dist_traveleds", [int(gtfs_route['route_id'])])
		
			for row in cursor.fetchall():
				trip_ids, stop_ids, stop_dist_traveleds = row

				cursor.execute("SELECT geom FROM patterns JOIN trips ON patterns.shape_id = trips.shape_id WHERE trips.trip_id = '%s'", [int(trip_ids[0])])
				pattern_geom = cursor.fetchone()[0]					
				
				# Create the pattern using the geometry of its trips.	
				pattern = api_models.Pattern(route=api_route,
											 geom=pattern_geom)
				
				if not self.dry_run:
					pattern.save()

				# Create the patternstops.
				for stop_order, stop_id in enumerate(stop_ids):
					stop = api_models.Stop.objects.get(pk=stop_id)
						
					ps = api_models.PatternStop(
						pattern=pattern,
						stop=stop,
						pattern_index=stop_order,
						pattern_dist_pct=stop_dist_traveleds[stop_order] / stop_dist_traveleds[-1],
						is_first_stop=stop_order==0,
						is_last_stop=stop_order==(len(stop_ids)-1))
	
					if not self.dry_run:
						ps.save()

