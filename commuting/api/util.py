def uniqify(seq):
	"""Given a list of elements, remove duplicates while preserving order."""
	seen = {} 
	result = [] 
	for item in seq: 
		if item in seen: continue 
		seen[item] = 1 
		result.append(item) 
	return result
