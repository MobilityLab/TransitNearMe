from django.db import connection
from django.core.management.base import BaseCommand, CommandError
from gtfs.models import Stop as GTFS_Stop
from api.models import Stop as API_Stop

class Command(BaseCommand):
	args = ''
	help = 'Imports GTFSDB data models to API database.'

	def handle(self, *args, **options):
		# Warn the user about erasing existing data.
		confirm = raw_input(u"""
You have requested to import GTFSDB data models into the API database.

This will erase all existing API database models.
Are you sure you want to do this?

Type 'yes' to continue, or 'no' to cancel: """)
		if confirm != 'yes':
			raise CommandError('Importing GTFSDB data models cancelled.')

		# Clear out existing DB tables.
		API_Stop.objects.all().delete()

		# Go through and import all of the tables.
		cursor = connection.cursor()
		gtfs_stops = GTFS_Stop.objects.all()
		for idx, gtfs_stop in enumerate(gtfs_stops):
			self.stdout.write('Converting stop %d/%d "%s".\n' % (idx + 1, len(gtfs_stops), gtfs_stop.stop_name))

			cursor.execute("SELECT routes.route_type FROM routes JOIN trips ON routes.route_id = trips.route_id JOIN stop_times ON trips.trip_id = stop_times.trip_id JOIN stops ON stop_times.stop_id = stops.stop_id WHERE stops.stop_id = '%s'", [int(gtfs_stop.stop_id)])
			route_type=cursor.fetchone()[0]


			api_stop = API_Stop(stop_id=int(gtfs_stop.stop_id),
								stop_name=gtfs_stop.stop_name,
								route_type=route_type,
								geom=gtfs_stop.geom)
			api_stop.save()
		
		self.stdout.write('Successfully converted GTFS models.\n')
