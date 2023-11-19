#!/usr/bin/env python

import os


names = list()

for name in os.listdir('.'):
    if os.path.isdir(name) and not name.startswith('.git'):
        names.append(name)

html = """
<html>
<head>
<title>csv2read</title>
</head>
<body>
<ul>
""" + '\n'.join(f'<li><a href="{name}">{name}</a></li>' for name in sorted(names)) + """
</ul>
</body>
"""

with open('index.html', 'w') as fout:
    fout.write(html)
