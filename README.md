# hdslfilter

hdslfilter is a Python module which filters lists of simple Python data
structures according to a simple filter language.

# Description

The filter can be one filter expression of a series of them in one text
string with arbitrary formatting, comments, etc.

## Basic Example Usage

Take the following Python data structures:

```
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
```

Here is an example of using a filter expression:
```
from hdslfilter.filter import FilterExpression
filter = FilterExpression.from_string('name=="John Doe"')

if filter.match(john): print 'match john' # True
if filter.match(jane): print 'match jane' # False
```

## More Examples

A regular expression. Matches both jane and john:

```
name =~ /Doe/
```

Basic logical operators are available. Nested dicts can be specified with a
dot.  Matches both jane and john:

```
name=="John Doe" or location.country=="PL"
```

Basic list membership is also available. Matches john:

```
location.country in ["US" "UK"]
```

Here's one more example. Matches only jane:

```
location.country not in ["US" "UK"] and name != "John Doe"
```

Undefined values will fail to match. Matches neither john or jane:

```
nickname == "Jo"
```

Numbers work. Matches jane:

```
age==97
```

See examples/filter.py for runnable example code.


## Sieve

A Sieve is a series of filter expressions in one textual unit (such as a
text file).  It can be formatted to be easy to read and have comments.  Each
filter expression is separated by a comma. Example Sieve:

```
# match either John or Bob
name =~ /^John/;
name =~ /^Bob/;

# match anyone in USA or UK
location.country in ["US","UK"];
```

This sieve will match John only. Here's an example of using a Sieve in code:

```
from hdslfilter.filter import Sieve

data = {'x': 'a'}
sieve_src = "x=='a'; # test for a"

sieve = Sieve.from_str(sieve_src)
print sieve.match(data)
```

# Installation

```
python setup.py install
```

# Copyright and License

Copyright (C) 2016 Hurricane Labs

hdslfilter was written by Steve Benson for Hurricane Labs.

hdslfilter is free software; you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free
Software Foundation; either version 3, or (at your option) any later
version.

hdslfilter is distributed in the hope that it will be useful, but WITHOUT ANY
WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
details.

You should have received a copy of the GNU General Public License along with
this program; see the file LICENSE.  If not, see <http://www.gnu.org/licenses/>.
