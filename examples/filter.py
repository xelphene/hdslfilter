
from hdslfilter.filter import FilterExpression

john = { 
	'name': 'John Doe', 
	'age': 133,
	'location': {
		'city': 'Ono',
		'country': 'US'
	}
}
jane = {
	'name': 'Jane Doe',
	'age': 97,
	'location': {
		'city': 'Hel',
		'country': 'PL'
	}
}

test_expressions = [
	'name=="John Doe"',
	'name =~ /Doe/',
	'name=="John Doe" or location.country=="PL"',
	'location.country in ["US" "UK"]',
	'location.country not in ["US" "UK"] and name != "John Doe"',
	'nickname == "Jo"',
	'age==97'
]

for e in test_expressions:
	print e
	filter = FilterExpression.from_string(e)
	if filter.match(john): print '  -  match john'
	if filter.match(jane): print '  -  match jane'

