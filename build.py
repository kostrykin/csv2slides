#!/usr/bin/env python

import string
import os
import argparse
import csv
import re
from xml.dom import minidom

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def get_fields(fields_str):
    fields = list()
    for token in fields_str.split(','):
        if '-' in token:
            subtokens = token.split('-')
            assert len(subtokens) == 2
            for pos in range(int(subtokens[0]), int(subtokens[1]) + 1):
                fields.append(pos)
        else:
            fields.append(int(token))
    assert len(frozenset(fields)) == len(fields), 'Fields contain duplicates'
    return list(sorted(fields))


class Data:

    def __init__(self, csv_filepath, semantics_filepath):
        with open(csv_filepath) as fin:
            self.rows = [row for row in csv.reader(fin)]
        self.semantics = dict()
        self.topics = dict()
        semantics = minidom.parse(semantics_filepath).getElementsByTagName('semantics')[0]
        for skip_semantic in semantics.getElementsByTagName('skip'):
            for pos in get_fields(skip_semantic.attributes['fields'].value):
                assert pos not in self.semantics, f'Duplicate semantics for field {pos}'
                self.semantics[pos] = {'type': 'skip'}
        for chart_semantic in semantics.getElementsByTagName('chart'):
            legend = list()
            for item in chart_semantic.getElementsByTagName('item'):
                legend.append({'key': item.attributes['key'].value, 'label': item.firstChild.data, 'color': item.attributes['color'].value})
            for pos in get_fields(chart_semantic.attributes['fields'].value):
                assert pos not in self.semantics, f'Duplicate semantics for field {pos}'
                self.semantics[pos] = {'type': 'chart', 'legend': legend}

        for topic in semantics.getElementsByTagName('topic'):
            for pos in get_fields(topic.attributes['fields'].value):
                assert pos not in self.topics, f'Duplicate topics for field {pos}'
                self.topics[pos] = topic.firstChild.data

    def __len__(self):
        return len(self.rows[0])

    def get_field_title(self, pos):
        assert 0 <= pos < len(self)
        return self.rows[0][pos]

    def get_field_type(self, pos):
        for row in self.rows[1:]:
            if pos >= len(row):
                return str
            value = row[pos]
            if not re.match(r'^[0-9]+$', value):
                return str
        return int

    def get_field_values(self, pos):
        field_type = self.get_field_type(pos)
        return [field_type(row[pos]) for row in self.rows[1:]]

    def get_field_semantic(self, pos):
        if pos + 1 in self.semantics:
            return self.semantics[pos + 1]
        elif self.get_field_type(pos) is int:
            values = self.get_field_values(pos)
            return {'type': 'chart', 'legend': [{'key': value, 'label': value, 'color': '#ccc'} for value in values]}
        else:
            return {'type': 'text'}

    def render_html(self, pos):
        semantic = self.get_field_semantic(pos)
        if semantic['type'] == 'skip':
            return ''
        values = self.get_field_values(pos)
        if semantic['type'] == 'chart':
            content = f'<img src="chart{pos}.svg">'
        elif semantic['type'] == 'text':
            content = '<ol>' + ''.join([f'<li>{str(value)}</li>' for value in values if len(str(value)) > 0]) + '</ol>'
        else:
            raise ValueError(f'unknown semantic: {semantic["type"]}')
        return f"""
            <section>
                <h6>{self.topics.get(pos, '')}</h6>
                <p class="field_title">{self.get_field_title(pos)}</p>
                {content}
            </section>
            """

    def render_chart(self, pos, semantic):
        values = self.get_field_values(pos)
        frequencies, labels, colors = list(), list(), list()
        for legend_item in semantic['legend']:
            frequency = sum((str(value) == str(legend_item['key']) for value in values))
            if frequency == 0: continue
            frequencies.append(frequency)
            labels.append(legend_item['label'])
            colors.append(legend_item['color'])
        assert len(frequencies) > 0, f'pos: {pos}, values: {values}, keys: {[legend_item["key"] for legend_item in semantic["legend"]]}'
        fig = plt.figure()
        ax = fig.add_subplot(111)
        ax.pie(frequencies, labels=labels, colors=colors, autopct='%1.1f%%', shadow=True, normalize=True)
        fig.savefig(f'chart{pos}.svg')

    def render_charts(self):
        for pos in range(len(self)):
            semantic = self.get_field_semantic(pos)
            if semantic['type'] == 'chart':
                self.render_chart(pos, semantic)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('build_directory', type=str)
    parser.add_argument('--csv_input', type=str, default='data.csv')
    parser.add_argument('--semantics', type=str, default='semantics.xml')
    args = parser.parse_args()
    
    data = Data(args.csv_input, args.semantics)

    slides_html = '\n'.join([data.render_html(pos) for pos in range(len(data))])
    
    with open('template.html') as fin:
        template = string.Template(fin.read())
    index_html = template.substitute(dict(slides_html=slides_html))
    
    print(f'Building into: {args.build_directory}')
    os.chdir(args.build_directory)
    
    os.system('git init')
    os.system('git remote add origin https://github.com/hakimel/reveal.js')
    os.system('git fetch origin bddeb70f4ef18aca1e0e7a3feed3f7f91de9682f')
    os.system('git reset --hard FETCH_HEAD')
    
    with open('index.html', 'w') as fout:
        fout.write(index_html)

    data.render_charts()
