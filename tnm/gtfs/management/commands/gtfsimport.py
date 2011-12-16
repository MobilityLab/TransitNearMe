import hashlib
import os
import zipfile

from django.contrib.gis.geos import Point, LineString
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from optparse import make_option

from gtfs.models import Dataset, Shape

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
            'stop_times.txt',
            'calendar.txt']:
            if required_file not in archive_files:
                raise CommandError("Incomplete GTFS archive.")

        # Create the dataset.
        dataset = Dataset(name=self.dataset_name, md5=md5.hexdigest())
        if not self.dry_run:
            dataset.save()
        
        # Read in shapes, if they are specified.
        if 'shapes.txt' in archive_files:
            data = zf.read('shapes.txt')
            lines = filter(lambda x: x, data.split('\n')[1:])

            shapes = {}
            for line in lines:
                parts = line.split(',')
                shape_id = parts[0]
                pt = Point(
                    x=float(parts[1]), 
                    y=float(parts[2]))
                
                if shape_id not in shapes:
                    shapes[shape_id] = [pt]
                else:
                    shapes[shape_id] += [pt]
            
            for shape_id, line in shapes.iteritems():
                shape = Shape(
                    dataset=dataset,
                    shape_id=shape_id,
                    line=LineString(line))
                
                if not self.dry_run:
                    shape.save()

        if self.dry_run:
            self.stdout.write("This was just a dry run!\n")
