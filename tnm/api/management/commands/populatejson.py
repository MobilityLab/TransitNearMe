import inspect

from api import models
from api.util import enumerate_verbose as ev
from django.core.management.base import NoArgsCommand

class Command(NoArgsCommand):
    def handle_noargs(self, **options):
        json_base = getattr(models, 'JsonModel')
        for name in dir(models):
            attr = getattr(models, name)
            if inspect.isclass(attr) and attr.__base__ == json_base:
                for obj in ev(
                    attr.objects.all(),
                    "Populating JSON for %s..." % name):
                    
                    obj.save(json=True)
