from django.conf import settings
from django.core.management.base import NoArgsCommand, CommandError
from optparse import make_option

from transitapis.apis import get_apis
from transitapis.models import Stop
 
class Command(NoArgsCommand):
    option_list = NoArgsCommand.option_list + (
        make_option('--nowarning',
            action='store_false', dest='warning', default=True,
            help="Don't prompt the user with a warning about erasing data."),
        make_option('-n', '--dry-run',
            action='store_true', dest='dry_run', default=False,
            help="Do everything except modify the database."),
    )
    help = "Calls available transit APIs to get a list of stops."

    def handle_noargs(self, **options):
        self.warning = options['warning']
        self.dry_run = options['dry_run']

        if self.warning and not self.dry_run:
            confirm = raw_input(u"""
You have requested calling available transit APIs to get a list of stops.

Doing this will erase all existing stops stored for these APIs.
Are you sure you want to do this?

Type 'yes' to continue, or 'no' to cancel: """)

            if confirm != 'yes':
                raise CommandError("Stop refreshing cancelled.")

        if not self.dry_run:
            Stop.objects.all().delete()

        apis = get_apis()
        for api in apis.values():
            self.stdout.write("Calling API '%s'.\n" % api.name)
            
            for k, v in api.options.iteritems():
                self.stdout.write("Using option: %s = %s\n" % (k, v))

            stops = api.get_all_stops()
            for stop in stops:
                self.stdout.write("Found stop: '%s'\n" % stop.name)
                    
                if not self.dry_run:
                    stop.save()

            self.stdout.write('\n')
        
        if self.dry_run:
            self.stdout.write("This was just a dry run!\n")
