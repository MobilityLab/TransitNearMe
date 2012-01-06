from django.contrib.gis.geos import LineString, WKBReader
from django.contrib.gis.measure import D
from django.core.management.base import NoArgsCommand, CommandError
from django.db import connection, transaction
from optparse import make_option

from api.models import Agency, Stop, Route, RouteSegment, ServiceFromStop
from api.util import enumerate_verbose as ev

class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--clean',
            action='store_true', dest='clean', default=False,
            help="Clear TNM database before updating with new data."),
        make_option('--nowarning',
            action='store_false', dest='warning', default=True,
            help="Don't prompt about erasing data."),
        make_option('--encodelines',
            action='store_true', dest='encodelines', default=True,
            help="Convert paths to encoded polylines (default true)."),
    )
    help = "Updates TNM database from GTFS and transit APIs."
 
    def enumerate_verbose(self, iterable, msg):
        return ev(iterable, msg, stream=self.stdout)

    def handle_noargs(self, **options):
        self.warning = options['warning']
        self.encodelines = options['encodelines']
        
        # Warn the user about erasing the database.
        if self.warning:
            confirm = raw_input(u"""
Building the database will erase all existing data.
Are you sure you want to do this?

Type 'yes' to continue, or 'no' to cancel: """)

            if confirm != 'yes':
                raise CommandError("Database build cancelled.")

        self.stdout.write("Cleaning TNM database of existing data...")
        self.stdout.flush()            

        Agency.objects.all().delete()
        Stop.objects.all().delete()
        Route.objects.all().delete()
        RouteSegment.objects.all().delete()
        ServiceFromStop.objects.all().delete()
        self.stdout.write("done.\n")

        cursor = connection.cursor()
        
        # Process GTFS agencies, copying primary keys.
        self.stdout.write("Processing agencies.\n")
        cursor.execute("INSERT INTO api_agency(id, name) SELECT id, agency_name FROM gtfs_agency")
        transaction.commit_unless_managed()

        # Process GTFS routes, copying primary keys.
        self.stdout.write("Processing routes.\n")
        cursor.execute("INSERT INTO api_route(id, agency_id, short_name, long_name, route_type, color) SELECT gtfs_route.id, api_agency.id, route_short_name, route_long_name, route_type::int, route_color FROM api_agency INNER JOIN gtfs_agency ON api_agency.name = gtfs_agency.agency_name INNER JOIN gtfs_route ON gtfs_agency.id = gtfs_route.agency_id")
        transaction.commit_unless_managed()

        # Process GTFS stops, copying primary keys.
        self.stdout.write("Processing stops.\n")
        cursor.execute("INSERT INTO api_stop(id, name, location) SELECT id, stop_name, location FROM gtfs_stop")
        transaction.commit_unless_managed()
        
        # Process GTFS patterns.
        # Create route segments.     
        self.stdout.write("Computing pattern intersections.\n")
        cursor.execute("DROP TABLE IF EXISTS api_temp_intersections")
        cursor.execute("CREATE TEMP TABLE api_temp_intersections AS SELECT gtfs_patternstop.stop_id, gtfs_patternstop.pattern_id, gtfs_patternstop.order, ST_Line_Locate_Point(line, location) AS intersection FROM gtfs_stop INNER JOIN gtfs_patternstop ON gtfs_stop.id = gtfs_patternstop.stop_id INNER JOIN gtfs_pattern ON gtfs_patternstop.pattern_id = gtfs_pattern.id INNER JOIN gtfs_shape ON gtfs_pattern.shape_id = gtfs_shape.id")

        self.stdout.write("Creating route segments.\n")
        cursor.execute("DROP TABLE IF EXISTS api_temp_segments")
        cursor.execute("CREATE TEMP TABLE api_temp_segments AS SELECT DISTINCT from_stop_id, from_order, c.pattern_id, gtfs_pattern.route_id, ST_Line_Substring(line, LEAST(c.from_intersection, c.to_intersection), GREATEST(c.from_intersection, c.to_intersection)) AS line FROM (SELECT a.stop_id AS from_stop_id, a.order AS from_order, a.pattern_id, a.intersection AS from_intersection, b.intersection AS to_intersection FROM (SELECT stop_id, pattern_id, api_temp_intersections.order, intersection FROM api_temp_intersections) AS a INNER JOIN api_temp_intersections b ON a.pattern_id = b.pattern_id AND a.order = b.order - 1) AS c INNER JOIN gtfs_pattern ON c.pattern_id = gtfs_pattern.id INNER JOIN gtfs_shape ON gtfs_pattern.shape_id = gtfs_shape.id")
        cursor.execute("CREATE INDEX line_index ON api_temp_segments USING GIST(line)")

        cursor.execute("INSERT INTO api_routesegment(line) SELECT DISTINCT line FROM api_temp_segments WHERE GeometryType(line) = 'LINESTRING'")
        transaction.commit_unless_managed()
        
        # Get unique services from stops.
        self.stdout.write("Determining stop services.\n")
        cursor.execute("DROP TABLE IF EXISTS api_temp_stop_service_patterns")
        cursor.execute("CREATE TEMP TABLE api_temp_stop_service_patterns AS SELECT y.pattern_id, stop_id, gtfs_patternstop.order as stop_order, route_id, destination_id FROM gtfs_patternstop INNER JOIN (SELECT pattern_id, route_id, destination_id, max_order FROM gtfs_pattern INNER JOIN (SELECT ps.pattern_id, ps.stop_id AS destination_id, max_order FROM gtfs_patternstop ps INNER JOIN (SELECT pattern_id, max(gtfs_patternstop.order) AS max_order FROM gtfs_patternstop GROUP BY pattern_id) AS gps ON ps.pattern_id = gps.pattern_id AND ps.order = gps.max_order) AS x ON gtfs_pattern.id = x.pattern_id) AS y ON gtfs_patternstop.pattern_id = y.pattern_id WHERE gtfs_patternstop.order != max_order")

        # Create ServiceFromStop objects.
        cursor.execute("INSERT INTO api_servicefromstop(stop_id, route_id, destination_id) SELECT DISTINCT stop_id, route_id, destination_id FROM api_temp_stop_service_patterns")
        transaction.commit_unless_managed()
        
        # Associate route segments with stop segments.
        # This JOIN can be huge, so do it incrementally.
        route_ids = [v['id'] for v in Route.objects.values('id')]
        for route_id in self.enumerate_verbose(
            route_ids,
            "Associating stop services with route segments"):
            
            cursor.execute("INSERT INTO api_servicefromstop_segments(servicefromstop_id, routesegment_id) SELECT DISTINCT sfs.id, rs_id FROM (SELECT rs_id, ssp.stop_id, ssp.route_id, ssp.destination_id FROM (SELECT rs.id AS rs_id, gtfs_ps.pattern_id, gtfs_ps.stop_id, gtfs_ps.order AS stop_order FROM api_routesegment rs INNER JOIN api_temp_segments seg ON ST_AsBinary(rs.line) = ST_AsBinary(seg.line) INNER JOIN gtfs_patternstop gtfs_ps ON seg.from_stop_id = gtfs_ps.stop_id INNER JOIN gtfs_pattern ON gtfs_pattern.id = gtfs_ps.pattern_id WHERE gtfs_pattern.route_id = seg.route_id) AS x INNER JOIN api_temp_stop_service_patterns ssp ON x.pattern_id = ssp.pattern_id AND x.stop_order >= ssp.stop_order AND ssp.route_id = %s) AS y INNER JOIN api_servicefromstop sfs ON y.stop_id = sfs.stop_id AND y.route_id = sfs.route_id AND y.destination_id = sfs.destination_id", [route_id])
            transaction.commit_unless_managed()

        if self.encodelines:
            for segment in self.enumerate_verbose(
                RouteSegment.objects.all(),
                "Creating encoded polylines"):
                
                segment.save()

