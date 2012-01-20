import json
import shapefile

from django.contrib.gis.geos import LineString
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from gtfs.models import Agency, Route
from urllib import urlencode
from urllib2 import urlopen

class Command(BaseCommand):
    args = 'agency_name shapefile_base [srid]'
    can_import_settings = False
    help = "Adds or replaces route pattern shapes from ESRI shapefile."

    @transaction.commit_on_success
    def handle(self, *args, **options):
        
        # Parse arguments.
        if len(args) < 2 or len(args) > 3:
            raise CommandError("Missing arguments. Try running with --help.")

        shapefile_base = args[0]
        agency_name = args[1]
        srid = int(args[2]) if len(args) > 2 else None

        # Verify the agency name.
        try:
            agency = Agency.objects.get(agency_name=agency_name)
        except Agency.DoesNotExist:
            self.stderr.write("No agency found for '%s'.\n" % agency_name)
            if Agency.objects.all():
                self.stderr.write("Agency name must be one of:\n")
                for agency in Agency.objects.all():
                    self.stderr.write("- %s\n" % agency.agency_name)
            return
    
        # Read in the shapefile.
        self.stdout.write("Reading shapefile from '%s'.\n" % shapefile_base)
        sf = shapefile.Reader(shapefile_base)

        # Verify that there is a NAME field in this shapefile.
        # Ignore first field ('DeletionField' added by shapefile library).
        name_index = [f[0] for f in sf.fields[1:]].index('NAME')

        if not srid:
            # Try opening a .prj file to get the shapefile projection.
            prj_file = open(shapefile_base + '.prj')
            prj_text = prj_file.read()

            # Connect to API to get SRID from projection, if not provided.
            # Inspired by http://gis.stackexchange.com/a/7784
            self.stdout.write("Querying prj2epsg to find SRID.\n")
            url = 'http://prj2epsg.org/search.json'
            query = urlencode(
                {'exact': True,
                 'error': True,
                 'mode': 'wkt',
                 'terms': prj_text})
            response = urlopen(url, query)
            data = json.loads(response.read())
            srid = int(data['codes'][0]['code'])
            self.stdout.write("Using SRID %d.\n" % srid)

        for shaperecord in sf.shapeRecords():
            shape = shaperecord.shape
            record = shaperecord.record

            # Get name of the record.
            name = record[name_index]
            self.stdout.write("Finding patterns for shape '%s'.\n" % name)

            # Verify that this shape is a PolyLine (type 3).
            if 3 != shape.shapeType:
                pass

            # Create the LineString with the appropriate SRID
            ls = LineString([list(pt) for pt in shape.points], srid=srid)

            # Transform into a common SRID (4326).
            ls.transform(4326)

            # Find the routes and patterns that are covered by this shape.
            # Consider all patterns where both the start and end stops are
            # within a certain distance to the shape.
            distance_threshold = 1609

            cursor = connection.cursor()

            # Find matching pattern ID, shape ID, and first and last stop locations.
            query = 'SELECT a.pattern_id, gp.shape_id, first_stop_location, last_stop_location FROM (SELECT pattern_id, gs.stop_id AS first_stop_id, location AS first_stop_location, stop_name AS first_stop_name FROM gtfs_patternstop gps INNER JOIN gtfs_stop gs ON gps.stop_id = gs.id WHERE gps.order = 0) a INNER JOIN (SELECT gps.pattern_id, gs.stop_id AS last_stop_id, location AS last_stop_location, stop_name AS last_stop_name FROM gtfs_patternstop gps INNER JOIN (SELECT pattern_id, MAX(gps.order) max_order FROM gtfs_patternstop gps GROUP BY pattern_id) gps2 ON gps.pattern_id = gps2.pattern_id AND gps.order = gps2.max_order INNER JOIN gtfs_stop gs ON gps.stop_id = gs.id) b ON a.pattern_id = b.pattern_id INNER JOIN gtfs_pattern gp ON a.pattern_id = gp.id INNER JOIN gtfs_route gr ON gp.route_id = gr.id WHERE gr.agency_id = %s AND ST_Distance_Sphere(first_stop_location, ST_Line_Interpolate_Point(ST_GeomFromEWKB(%s), ST_Line_Locate_Point(ST_GeomFromEWKB(%s), first_stop_location))) < %s AND ST_Distance_Sphere(last_stop_location, ST_Line_Interpolate_Point(ST_GeomFromEWKB(%s), ST_Line_Locate_Point(ST_GeomFromEWKB(%s), last_stop_location))) < %s AND (gr.route_short_name ILIKE %s OR gr.route_long_name ILIKE %s) AND gp.shape_id IS NOT NULL'
            args = [agency.id, ls.ewkb, ls.ewkb, distance_threshold, ls.ewkb, ls.ewkb, distance_threshold, name, name]

            cursor.execute(query, args)
            data = cursor.fetchall()

            for row in data:

                pattern_id = row[0]
                shape_id = row[1]
                first_stop_location = row[2]
                last_stop_location = row[3]
            
                # Cut the shape between the first and last stops.
                query = 'SELECT ST_Line_Substring(ST_GeomFromEWKB(%s), LEAST(ST_Line_Locate_Point(%s, %s), ST_Line_Locate_Point(%s, %s)), GREATEST(ST_Line_Locate_Point(%s, %s), ST_Line_Locate_Point(%s, %s)))'
                args = [ls.ewkb, ls.ewkb, first_stop_location, ls.ewkb, last_stop_location, ls.ewkb, first_stop_location, ls.ewkb, last_stop_location]
                cursor.execute(query, args)
                substring = cursor.fetchall()[0]

                # Update the database with the new partial shape.
                query = 'UPDATE gtfs_shape SET line=%s WHERE id=%s'
                args = [substring, shape_id]

                cursor.execute(query, args)
                transaction.commit_unless_managed()
