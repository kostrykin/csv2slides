#!/usr/bin/env python

import string
import os
import argparse


parser = argparse.ArgumentParser()
parser.add_argument('build_directory')
args = parser.parse_args()


with open('template.html') as fin:
    template = string.Template(fin.read())

slides_html = """
<section>
    hello world
    <div><canvas id="chart1"></canvas></div>
</section>"""

slides_js = """
const ctx1 = document.getElementById('chart1');
new Chart(ctx1, {
    type: 'bar',
    data: {
      labels: ['Red', 'Blue', 'Yellow', 'Green', 'Purple', 'Orange'],
      datasets: [{
        label: '# of Votes',
        data: [12, 19, 3, 5, 2, 3],
        borderWidth: 1
      }]
    },
    options: {
      scales: {
        y: {
          beginAtZero: true
        }
      }
    }
  });
"""

index_html = template.substitute(dict(slides_html=slides_html, slides_js=slides_js))

print(f'Building into: {args.build_directory}')
os.chdir(args.build_directory)

os.system('git init')
os.system('git remote add origin https://github.com/hakimel/reveal.js')
os.system('git fetch origin bddeb70f4ef18aca1e0e7a3feed3f7f91de9682f')
os.system('git reset --hard FETCH_HEAD')

with open('index.html', 'w') as fout:
    fout.write(index_html)
