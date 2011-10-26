import os
os.environ['DJANGO_SETTINGS_MODULE'] = 'localtransit.settings'

import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'localtransit'))

import django.core.handlers.wsgi
application = django.core.handlers.wsgi.WSGIHandler()
