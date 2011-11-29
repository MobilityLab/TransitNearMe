class hashabledict(dict):
    def __hash__(self):
        return hash(tuple(sorted(self.items())))    

def uniqify(seq):
	"""Given a list of elements, remove duplicates while preserving order."""
	seen = {} 
	result = [] 
	for item in seq: 
	    if isinstance(item, dict):
                item = hashabledict(item)

            if item in seen: continue 
	    seen[item] = 1 
	    result.append(item) 
	return result
