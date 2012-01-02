from django.contrib.gis.measure import D
from django.core.management.base import NoArgsCommand, CommandError
from django.db import connection, transaction
from optparse import make_option

from api.models import Agency, Stop, Route, RouteSegment, ServiceFromStop
from api.util import enumerate_verbose as ev
from gtfs import models as gtfs_models
from transitapis import models as transitapis_models

class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('-n', '--dry-run',
            action='store_true', dest='dry_run', default=False,
            help="Do everything except modify the TNM database."),
        make_option('--clean',
            action='store_true', dest='clean', default=False,
            help="Clear TNM database before updating with new data."),
        make_option('--nowarning',
            action='store_false', dest='warning', default=True,
            help="Don't prompt about erasing data."),
    )
    help = "Updates TNM database from GTFS and transit APIs."
 
    def enumerate_verbose(self, iterable, msg):
        ev(iterable, msg, stream=self.stdout)

    #@transaction.commit_on_success
    def handle_noargs(self, **options):
        self.dry_run = options['dry_run']
        self.warning = options['warning']
        
        # Warn the user about erasing the database.
        if self.warning and not self.dry_run:
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

        # Process GTFS agencies.
        agencies = {}
        for gtfs_agency in self.enumerate_verbose(
            gtfs_models.Agency.objects.all(),
            "Processing agencies"):

            agency = Agency(
                name=gtfs_agency.agency_name)
            agencies[gtfs_agency] = agency
            
            if not self.dry_run:
                agency.save()

        # Process GTFS routes.
        routes = {}
        for gtfs_route in self.enumerate_verbose(
            gtfs_models.Route.objects.all(),
            "Processing routes"):

            route = Route(
                agency=agencies[gtfs_route.agency],
                short_name=gtfs_route.route_short_name,
                long_name=gtfs_route.route_long_name,
                route_type=gtfs_route.route_type,
                color=gtfs_route.route_color)
            routes[gtfs_route] = route

            if not self.dry_run:
                route.save()

        # Process GTFS stops.
        stops = {}
        for gtfs_stop in self.enumerate_verbose(
            gtfs_models.Stop.objects.all(),
            "Processing stops"):
            
            stop = Stop(
                name=gtfs_stop.stop_name,
                location=gtfs_stop.location)
            stops[gtfs_stop] = stop

            if not self.dry_run:
                stop.save()

        # Process GTFS patterns.
        cursor = connection.cursor()
        for gtfs_pattern in self.enumerate_verbose(
            gtfs_models.Pattern.objects.all(),
            "Processing patterns"):

            gtfs_pattern_stops = gtfs_pattern.patternstop_set.order_by('order')
            num_pattern_stops = len(gtfs_pattern_stops)
            last_stop = stops[gtfs_pattern_stops[num_pattern_stops-1].stop]

            for pattern_index, pattern_stop in enumerate(gtfs_pattern_stops):

                # Skip the last stop since the pattern only goes to itself.
                if pattern_index == num_pattern_stops - 1:
                    continue
            
                gtfs_stop = pattern_stop.stop
                stop = stops[gtfs_stop]

                # Generate the geometry for this pattern.
                routesegment = None
                gtfs_shape = gtfs_pattern.shape

                if gtfs_shape:
                    # Cut the shape into the portion covered by this pattern.
                    # This operation fails in certain circumstances.
                    try:
                        sid = transaction.savepoint()

                        cursor.execute("SELECT ST_Line_Substring(ST_GeomFromEWKT(%s), ST_Line_Locate_Point(ST_GeomFromEWKT(%s), ST_GeomFromEWKT(%s)), 1)", [gtfs_shape.line.ewkt, gtfs_shape.line.ewkt, gtfs_stop.location.ewkt])
                        partial_line = cursor.fetchone()[0]
                    except:
                        self.stderr.write("\rFailed to create geometry for GTFS pattern %s.\n" % gtfs_pattern.id)
                        transaction.savepoint_commit(sid)
                        continue

                    try:
                        routesegment = RouteSegment.objects.get(
                            line=partial_line)
                    except RouteSegment.DoesNotExist:
                        routesegment = RouteSegment(
                            line=partial_line)

                    if not self.dry_run:
                        try:
                            routesegment.save()
                        except TypeError:
                            self.stderr.write("\rFailed to create geometry for GTFS pattern %s.\n" % gtfs_pattern.id)
                            routesegment = None

                try:
                    service = ServiceFromStop.objects.get(
                        stop=stop,
                        route=routes[gtfs_pattern.route],
                        destination=last_stop,
                        segments=routesegment)
                except ServiceFromStop.DoesNotExist:
                    service = ServiceFromStop(
                        stop=stop,
                        route=routes[gtfs_pattern.route],
                        destination=last_stop)

                    if not self.dry_run:
                        service.save()
                        if routesegment:
                            service.segments.add(routesegment)

