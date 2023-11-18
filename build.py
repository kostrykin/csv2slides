#!/usr/bin/env python

import string
import os
import argparse


parser = argparse.ArgumentParser()
parser.add_argument('build_directory')
args = parser.parse_args()


with open('template.html') as fin:
    template = string.Template(fin.read())

slides_html = '<section>hello world</section>'

index_html = template.substitute(dict(slides=slides_html))

print(f'Building into: {args.build_directory}')
os.chdir(args.build_directory)

os.system('git init')
os.system('git remote add origin https://github.com/hakimel/reveal.js')
os.system('git fetch origin bddeb70f4ef18aca1e0e7a3feed3f7f91de9682f')
os.system('git reset --hard FETCH_HEAD')

with open('index.html', 'w') as fout:
    fout.write(index_html)
