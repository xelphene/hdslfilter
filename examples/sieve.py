
from hdslfilter.filter import Sieve

# example data structures to match
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

# example sieve to match them against
sieve_src = '''

# match either John or Bob
name =~ /^John/;
name =~ /^Bob/;

# match anyone in USA or UK
location.country in ["US","UK"];

'''

sieve = Sieve.from_str(sieve_src)

print 'john:',sieve.match(john)
print 'jane:',sieve.match(jane)
