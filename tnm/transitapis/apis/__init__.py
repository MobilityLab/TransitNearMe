from django.conf import settings

def get_apis():
    """
    Returns a dictionary of transit APIs as specified in the project settings.

    Each API is defined by a name that describes it, a class name which is
    used to actually create it, and an options dictionary that gets passed to
    the class at creation time.

    Here's an example of what a settings section might look like:

    TRANSIT_APIS = {
        'Metrorail': (
            'transitapis.apis.wmata.Metrorail',
            { 'key': 'my-api-key', }
        ),
    }

    API classes inherit from transitapis.apis.base.Base and share a common
    constructor pattern. For the example above, the API object could be
    created like this:

        from transitapis.apis.wmata import Metrorail
        api = Metrorail(name='Metrorail', options={'key': 'my-api-key'})

    Different API classes require different options to be passed in at
    creation time. Consult individual class documentation for details.

    """
    api_settings = settings.TRANSIT_APIS
    
    apis = {}
    for api_name, api_tuple in api_settings.iteritems():
        api_cls = api_tuple[0]
        api_options = {}
        if len(api_tuple) > 1:
            api_options = api_tuple[1]

        cls_parts = api_cls.split('.')
        cls = __import__('.'.join(cls_parts[:-1]))
        for cls_part in cls_parts[1:]:
            cls = getattr(cls, cls_part)

        api = cls(name=api_name, options=api_options)
        apis[api_name] = api
    
    return apis
        
