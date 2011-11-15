from collections import defaultdict
from django.shortcuts import render

from transitfeeds.models import Query, RailPrediction

def waits(request, template_name):
	waits = []	

	recent_queries = Query.objects.exclude(railprediction__line__isnull=True).reverse()[:120]
	recent_queries = [rq.id for rq in recent_queries]

	lines = ['OR', 'RD', 'YL', 'GR', 'BL']
	good_predictions = RailPrediction.objects.filter(query__in=recent_queries, line__in=lines).order_by('location_name', 'group', 'line')

	combinations = good_predictions.values('location_name', 'group', 'line').distinct()

	for combination in combinations:
		location_name = combination['location_name']
		group = combination['group']
		line = combination['line']

		predictions = good_predictions.filter(location_name=location_name,
											  group=group,
											  line=line)
		
		if not predictions:
			continue
	
		destinations = predictions.values('destination_name').distinct()
		destinations = [destination['destination_name'] for destination in destinations]

		preds = defaultdict(list)
		for p in predictions:
			preds[p.query.id].append(p.wait)

		wait_times = []
		for rqid in recent_queries:
			if not rqid in preds:
				continue

			min_wait = min(preds[rqid])
			if min_wait is not None:
				wait_times.append(str(min_wait))
			else:
				wait_times.append('null')

		wait = {'location_name': location_name,
				'line': line,
				'group': group,
				'destinations': ', '.join(destinations),
				'wait_times': ','.join(wait_times) }
		waits.append(wait)
	
	return render(request, template_name, { 'waits': waits })
