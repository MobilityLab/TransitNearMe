import codecs
import csv
import hashlib
import os
import zipfile

from django.contrib.gis.geos import Point, LineString
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from optparse import make_option

from gtfs.models import *

def read_lines_from_zipfile(zf, filename):
    data = zf.read(filename)
    if data.startswith(codecs.BOM_UTF8):
        data = data.decode('utf-8-sig')
    
    lines = map(lambda x: x.rstrip('\r'), data.split('\n'))
    headings = dict(enumerate(lines[0].split(',')))
    
    lines = filter(lambda x: x, lines[1:])
    for i, line in enumerate(csv.reader(lines)):
        yield dict(zip(headings.values(), line)), int(100 * i / len(lines))

class Command(BaseCommand):
    args = 'gtfs_archive.zip dataset_name'
    can_import_settings = False
    help = "Imports GTFS archive as a new dataset."
    option_list = BaseCommand.option_list + (
        make_option('-n', '--dry-run',
            action='store_true', dest='dry_run', default=False,
            help="Do everything except modify the database."),
    )

    @transaction.commit_on_success
    def handle(self, *args, **options):
        self.dry_run = options['dry_run']

        # Parse arguments.
        if 2 != len(args):
            raise CommandError("Missing arguments. Try running with --help.")

        self.filename = args[0]
        self.dataset_name = args[1]

        # Compute md5 of archive for reference purposes.
        md5 = hashlib.md5()
        with open(self.filename, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), ''):
                md5.update(chunk)

        zf = zipfile.ZipFile(self.filename, 'r')
        archive_files = zf.namelist()

        # Check for files required by the GTFS specification.
        for required_file in [
            'agency.txt',
            'stops.txt',
            'routes.txt',
            'trips.txt',
            'stop_times.txt']:
            if required_file not in archive_files:
                raise CommandError("Incomplete GTFS archive.")

        # Create the dataset.
        dataset = Dataset(name=self.dataset_name, md5=md5.hexdigest())
        if not self.dry_run:
            dataset.save()

        # Read in agencies.
        agencies = {}
        for parts, pct in read_lines_from_zipfile(zf, 'agency.txt'):
            self.stdout.write("\rReading agencies...%s%%" % pct)
            self.stdout.flush()

            agency = Agency(
                dataset=dataset,
                agency_id=parts.get('agency_id', None),
                agency_name=parts['agency_name'])
            if agency.agency_id:
                agencies[agency.agency_id] = agency
            
            if not self.dry_run:
                agency.save()

        self.stdout.write("\rReading agencies...done.\n")       
 
        # Read in stops.
        stops = {}
        for parts, pct in read_lines_from_zipfile(zf, 'stops.txt'):
            self.stdout.write("\rReading stops...%s%%" % pct)
            self.stdout.flush()

            stop = Stop(
                dataset=dataset,
                stop_id=parts['stop_id'],
                stop_name=parts['stop_name'],
                location=Point(
                    x=float(parts['stop_lon']),
                    y=float(parts['stop_lat'])))
            stops[stop.stop_id] = stop

            if not self.dry_run:
                stop.save()
            
        self.stdout.write("\rReading stops...done.\n")    

        # Read in routes.
        routes = {}
        for parts, pct in read_lines_from_zipfile(zf, 'routes.txt'):
            self.stdout.write("\rReading routes...%s%%" % pct)
            self.stdout.flush()

            agency_id = parts.get('agency_id', None)
            agency = agencies.get(agency_id, None)

            route = Route(
                route_id=parts['route_id'],
                agency=agency,
                route_short_name=parts['route_short_name'],
                route_long_name=parts['route_long_name'],
                route_type=parts['route_type'],
                route_color=parts.get('route_color', None))
            routes[route.route_id] = route

            if not self.dry_run:
                route.save()            
        
        self.stdout.write("\rReading routes...done.\n")

        # Read in shapes, if they are specified.
        if 'shapes.txt' in archive_files:
            lines = {}
            for parts, pct in read_lines_from_zipfile(zf, 'shapes.txt'):
                self.stdout.write("\rReading shapes...%s%%" % pct)
                self.stdout.flush()

                shape_id = parts['shape_id']
                shape_pt_lon = float(parts['shape_pt_lon'])
                shape_pt_lat = float(parts['shape_pt_lat'])
                shape_pt = Point(x=shape_pt_lon, y=shape_pt_lat)
                
                if shape_id not in lines:
                    lines[shape_id] = [shape_pt]
                else:
                    lines[shape_id] += [shape_pt]
            
            self.stdout.write("\rReading shapes...done.\n")

            # Compute EWKT of each linestring to help with finding duplicates.
            linestrings = {}
            ewkts = {}
            for shape_id, line in lines.iteritems():
                linestrings[shape_id] = LineString(lines[shape_id], srid=4326)
                ewkts[shape_id] = linestrings[shape_id].ewkt
 
            shapes = {}
            unique_shapes = []
            for i, shape_id in enumerate(linestrings.keys()):
                pct = 100 * i / len(linestrings)
                self.stdout.write("\rSaving shapes...%s%%" % pct)
                self.stdout.flush()

                shape = None
                for unique_shape in unique_shapes:
                    if unique_shape.line.ewkt == ewkts[shape_id]:
                        shape = unique_shape
                        shape.shape_ids += ',' + shape_id
                        break

                if not shape:
                    shape = Shape(
                        dataset=dataset,
                        shape_ids=shape_id,
                        line=linestrings[shape_id])
                    unique_shapes += [shape]
                    
                shapes[shape_id] = shape
                
            if not self.dry_run:
                for shape in unique_shapes:
                    shape.save()

            self.stdout.write("\rSaving shapes...done.\n")
    
        # Read in stop times and trips.
        trips = {}
        for parts, pct in read_lines_from_zipfile(zf, 'stop_times.txt'):
            self.stdout.write("\rReading stop times...%s%%" % pct)
            self.stdout.flush()

            trip_id = parts['trip_id']
            stop_id = parts['stop_id']

            if trip_id not in trips:
                trips[trip_id] = [stop_id]
            else:
                trips[trip_id] += [stop_id]
        self.stdout.write("\rReading stop times...done.\n")

        pattern_keys = []
        for parts, pct in read_lines_from_zipfile(zf, 'trips.txt'):
            self.stdout.write("\rReading trips...%s%%" % pct)
            self.stdout.flush()
           
            shape_id = parts.get('shape_id', None)
            shape = shapes.get(shape_id, None)
           
            route_id = parts['route_id']
            route = routes[route_id]

            pattern = Pattern(
                route=route,
                shape=shape)

            patternstops = []
            trip_id = parts['trip_id']
            for stop_order, stop_id in enumerate(trips[trip_id]):
                stop = stops[stop_id] 
        
                patternstop = PatternStop(
                    pattern=pattern,
                    stop=stop,
                    order=stop_order)
                patternstops += [patternstop]

            if not self.dry_run:            
                key = [pattern.route.id]
                if pattern.shape:
                    key += [pattern.shape.id]
                for patternstop in patternstops:
                    key += [patternstop.stop.id, patternstop.order]

                if key not in pattern_keys:
                    pattern_keys += [key]

                    pattern.save()
                    for patternstop in patternstops:
                        patternstop.pattern = pattern
                        patternstop.save()
                
        self.stdout.write("\rReading trips...done.\n")

        if self.dry_run:
            self.stdout.write("This was just a dry run!\n")
