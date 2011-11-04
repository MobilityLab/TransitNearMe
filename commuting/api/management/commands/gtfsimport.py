from optparse import make_option

from django.db import connection
from django.core.management.base import NoArgsCommand, CommandError

from gtfs import models as gtfs_models
from api import models as api_models


class Command(NoArgsCommand):
	option_list = NoArgsCommand.option_list + (
		make_option('--nowarning',
			action='store_false', dest='warning', default=True,
			help="Don't prompt the user with a warning about erasing data."),
		make_option('-n', '--dry-run',
			action='store_true', dest='dry_run', default=False,
			help="Do everything except modify the database."),
		make_option('--nostops',
			action='store_false', dest='do_stops', default=True,
			help="Don't process stops table."),
		make_option('--nopatterns',
			action='store_false', dest='do_patterns', default=True,
			help="Don't process patterns tables."),
	)
	help = "Imports GTFSDB data models to API database."

	def handle_noargs(self, **options):
		self.warning = options['warning']
		self.dry_run = options['dry_run']
		self.do_stops = options['do_stops']
		self.do_patterns = options['do_patterns']

		if self.warning:
			# Warn the user about erasing existing data.
			confirm = raw_input(u"""
You have requested to import GTFSDB data models into the API database.

This will erase all existing API database models.
Are you sure you want to do this?

Type 'yes' to continue, or 'no' to cancel: """)
			
			if confirm != 'yes':
				raise CommandError("Importing GTFSDB data models cancelled.")

		if self.do_stops:
			self.process_stops()

		if self.do_patterns:
			self.process_patterns()

		self.stdout.write("Successfully converted GTFS models.\n")		
		if self.dry_run:
			self.stdout.write("This was just a dry run!\n")

	def process_stops(self):
		if not self.dry_run:
			# Clear out existing DB tables.
			api_models.Stop.objects.all().delete()
		
		# Read in stop information.
		cursor = connection.cursor()
		gtfs_stops = gtfs_models.Stop.objects.all()
		
		for idx, gtfs_stop in enumerate(gtfs_stops):
			self.stdout.write("Converting stop %d/%d '%s'.\n" % (idx + 1, len(gtfs_stops), gtfs_stop.stop_name))

			cursor.execute("SELECT routes.route_type FROM routes JOIN trips ON routes.route_id = trips.route_id JOIN stop_times ON trips.trip_id = stop_times.trip_id JOIN stops ON stop_times.stop_id = stops.stop_id WHERE stops.stop_id = '%s'", [int(gtfs_stop.stop_id)])
			route_type = cursor.fetchone()[0]

			api_stop = api_models.Stop(stop_id=int(gtfs_stop.stop_id),
									   stop_name=gtfs_stop.stop_name,
									   route_type=route_type,
									   geom=gtfs_stop.geom)
			
			if not self.dry_run:
				api_stop.save()

	def process_patterns(self):
		if not self.dry_run:
			# Clear out existing DB tables.
			api_models.Pattern.objects.all().delete()
			api_models.PatternStop.objects.all().delete()
		
		# Read in pattern information.
		cursor = connection.cursor()		
		gtfs_routes = gtfs_models.Route.objects.all()
		
		for idx, gtfs_route in enumerate(gtfs_routes):
			self.stdout.write("Converting route %d/%d '%s'.\n" % (idx + 1, len(gtfs_routes), gtfs_route.route_short_name))

			cursor.execute("SELECT array_agg(unique_patterns.trip_id), unique_patterns.stop_ids FROM (SELECT patterns.trip_id, array_agg(patterns.stop_id) AS stop_ids FROM (SELECT trips.trip_id, stops.stop_id, stop_times.stop_sequence FROM stop_times JOIN stops ON stop_times.stop_id = stops.stop_id JOIN trips ON stop_times.trip_id = trips.trip_id WHERE trips.route_id = '%s' ORDER BY trips.trip_id, stop_times.stop_sequence) AS patterns GROUP BY patterns.trip_id) AS unique_patterns GROUP BY unique_patterns.stop_ids", [int(gtfs_route.route_id)])
		
			for row in cursor.fetchall():
				trip_ids, stop_ids = row

				cursor.execute("SELECT geom FROM patterns JOIN trips ON patterns.shape_id = trips.shape_id WHERE trips.trip_id = '%s'", [int(trip_ids[0])])
				pattern_geom = cursor.fetchone()[0]					
				
				# Create the pattern using the geometry of its trips.	
				pattern = api_models.Pattern(geom=pattern_geom,
											 color=gtfs_route.route_color,
											 name=gtfs_route.route_short_name)
				if not self.dry_run:
					pattern.save()

				# Create the patternstops.
				for stop_order, stop_id in enumerate(stop_ids):
					stop = api_models.Stop.objects.get(pk=stop_id)
						
					ps = api_models.PatternStop(
						pattern=pattern,
						pattern_index=stop_order,
						stop=stop,
						is_first_stop=stop_order==0,
						is_last_stop=stop_order==(len(stop_ids)-1))
	
					if not self.dry_run:
						ps.save()

