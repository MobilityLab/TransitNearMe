from optparse import make_option
from django.db import connection, transaction
from django.core.management.base import BaseCommand, CommandError

from api.models import *

def dictfetchall(cursor):
    """Returns all rows from a cursor as a dict."""
    desc = cursor.description
    return [
            dict(zip([col[0] for col in desc], row))
            for row in cursor.fetchall()
    ]   

class Command(BaseCommand):
    args = 'dataset_name'
    can_import_settings = False
    help = "Imports GTFSDB data models to API database."

    def handle(self, *args, **options):
        if 1 != len(args):
            raise CommandError("Specify dataset name.")
        
        self.dataset_name = args[0]

        # Create a new dataset.
        dataset = Dataset(name=self.dataset_name)
        dataset.save()

        self.process_agencies(dataset)
        self.process_stops(dataset)
        self.process_routes(dataset)

        self.stdout.write("Successfully converted GTFS models.\n")              
    def process_agencies(self, dataset):
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM agency")
        gtfs_agencies = dictfetchall(cursor)
        
        for idx, gtfs_agency in enumerate(gtfs_agencies):
            self.stdout.write("Converting agency %d/%d '%s'.\n" % (idx + 1, len(gtfs_agencies), gtfs_agency['agency_name']))

            agency = Agency(
                dataset=dataset,
                gtfs_id=gtfs_agency['agency_id'],
                name=gtfs_agency['agency_name'])
            agency.save()

    def process_stops(self, dataset):
        # Read in stop information.
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM stops")
        gtfs_stops = dictfetchall(cursor)
   
        for idx, gtfs_stop in enumerate(gtfs_stops):
            self.stdout.write("Converting stop %d/%d '%s'.\n" % (idx + 1, len(gtfs_stops), gtfs_stop['stop_name']))

            api_stop = Stop(
                dataset=dataset,
                gtfs_id=gtfs_stop['stop_id'],
                name=gtfs_stop['stop_name'],
                location=gtfs_stop['geom'])
            api_stop.save()

    def process_routes(self, dataset):
        # Read in pattern information.
        cursor = connection.cursor()                
        cursor.execute("SELECT * FROM routes")
        gtfs_routes = dictfetchall(cursor)
               
        agencies = Agency.objects.filter(dataset=dataset)
 
        for idx, gtfs_route in enumerate(gtfs_routes):
            self.stdout.write("Converting route %d/%d '%s'.\n" % (idx + 1, len(gtfs_routes), gtfs_route['route_short_name']))

            if len(agencies) == 1:
                agency = agencies[0]
            else:
                agency = agencies.get(gtfs_id=gtfs_route['agency_id'])

            api_route, created = Route.objects.get_or_create(
                dataset=dataset,
                gtfs_id=gtfs_route['route_id'],
                agency=agency,
                short_name=gtfs_route['route_short_name'],
                long_name=gtfs_route['route_long_name'],
                route_type=gtfs_route['route_type'],
                color=gtfs_route['route_color'])

            cursor.execute("SELECT array_agg(unique_patterns.trip_id), unique_patterns.stop_ids, unique_patterns.shape_dist_traveleds FROM (SELECT patterns.trip_id, array_agg(patterns.stop_id) AS stop_ids, array_agg(patterns.shape_dist_traveled) AS shape_dist_traveleds FROM (SELECT trips.trip_id, stops.stop_id, stop_times.stop_sequence, stop_times.shape_dist_traveled FROM stop_times JOIN stops ON stop_times.stop_id = stops.stop_id JOIN trips ON stop_times.trip_id = trips.trip_id WHERE trips.route_id = '%s' ORDER BY trips.trip_id, stop_times.stop_sequence) AS patterns GROUP BY patterns.trip_id) AS unique_patterns GROUP BY unique_patterns.stop_ids, unique_patterns.shape_dist_traveleds", [int(gtfs_route['route_id'])])
            
            # Iterate over each trip.
            for row in cursor.fetchall():
                trip_ids, stop_ids, stop_dist_traveleds = row

                # Find the destination for this trip. 
                destination = Stop.objects.get(
                    gtfs_id=stop_ids[-1],
                    dataset=dataset)

                # Read in the geometry for this trip. 
                cursor.execute("SELECT geom FROM patterns JOIN trips ON patterns.shape_id = trips.shape_id WHERE trips.trip_id = '%s'", [int(trip_ids[0])])
                geom_result = cursor.fetchone()
                if geom_result:
                    trip_geom = geom_result[0]

                    segment, created = RouteSegment.objects.get_or_create(
                        dataset=dataset,
                        line=trip_geom)
                else:
                    segment = None
                    segment_subset = None

                # Iterate over each stop in the trip.
                for stop_order, stop_id in enumerate(stop_ids):
                    # Don't create a service from a stop to itself.
                    if stop_order == len(stop_ids) - 1:
                        continue

                    stop = Stop.objects.get(
                        gtfs_id=stop_id,
                        dataset=dataset)

                    if segment:
                        try: 
                            sid = transaction.savepoint()

                            # Cut the path at the origin stop, unless the trip
                            # starts and ends at the same stop.
                            if (stop_order == 0) and (stop_ids[0] == stop_ids[-1]):
                                segment_subset = segment
                            else: 
                                cursor.execute("SELECT ST_Line_Substring(ST_GeomFromEWKT(%s), ST_Line_Locate_Point(ST_GeomFromEWKT(%s), ST_GeomFromEWKT(%s)), 1)", [trip_geom, trip_geom, stop.location.ewkt])
                                trip_geom_subset = cursor.fetchone()[0]

                                segment_subset, created = RouteSegment.objects.get_or_create(
                                    dataset=dataset,
                                    line=trip_geom_subset)
                    
                            transaction.savepoint_commit(sid)
                        except:
                            self.stderr.write("Couldn't create trip geometry subset for route %s, segment %s, stop %s." % (api_route.id, segment.id, stop_id))
                            transaction.savepoint_rollback(sid)
                            continue

                    service, created = ServiceFromStop.objects.get_or_create(
                        dataset=dataset,
                        stop=stop,
                        route=api_route,
                        destination=destination)

                    if segment_subset:
                        service.segments.add(segment_subset)
                    
                    # Required to refresh service JSON.
                    service.save()
              
