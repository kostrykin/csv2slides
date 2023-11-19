#!/usr/bin/env python

import string
import os, os.path
import shutil
import argparse
import csv
import re
from xml.dom import minidom

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


def get_fields(fields_str, last_field=None):
    fields = list()
    for token in fields_str.split(','):
        if '-' in token:
            subtokens = token.split('-')
            assert len(subtokens) == 2
            for pos in range(int(subtokens[0]), int(subtokens[1]) + 1 if len(subtokens[1]) > 0 else last_field):
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
        semantics = minidom.parse(semantics_filepath).getElementsByTagName('semantics')[0]
        for chart_semantic in semantics.getElementsByTagName('chart'):
            legend = list()
            for item in chart_semantic.getElementsByTagName('item'):
                legend.append({'key': item.attributes['key'].value, 'label': item.firstChild.data, 'color': item.attributes['color'].value})
            for pos in get_fields(chart_semantic.attributes['fields'].value):
                assert pos not in self.semantics, f'Duplicate semantics for field {pos}'
                self.semantics[pos] = {'type': 'chart', 'legend': legend}

    def __len__(self):
        return len(self.rows[0])

    def get_field_title(self, pos):
        assert 0 <= pos < len(self)
        return self.rows[0][pos]

    def get_field_type(self, pos):
        undecided = True
        for row in self.rows[1:]:
            value = row[pos] if pos < len(row) else ''
            if len(value) == 0:
                continue
            if re.match(r'^[0-9]+$', value):
                undecided = False
            else:
                return str
        return str if undecided else int

    def get_field_values(self, pos):
        field_type = self.get_field_type(pos)
        return [field_type(row[pos]) for row in self.rows[1:] if len(row[pos]) > 0]

    def get_field_semantic(self, pos):
        semantic = self.semantics[pos + 1] if pos + 1 in self.semantics else None
        if (semantic is None and self.get_field_type(pos) is int) or (semantic is not None and semantic['type'] == 'chart' and len(semantic.get('legend', [])) == 0):
            values = list(frozenset(self.get_field_values(pos)))
            colors = [('#dfdfdf' if value_idx % 2 == 0 else '#efefef') for value_idx, _ in enumerate(values)]
            if len(colors) % 2 == 1: colors[-1] = '#cfcfcf'
            return {'type': 'chart', 'legend': [{'key': value, 'label': str(value), 'color': color} for value, color in zip(values, colors)]}
        elif semantic is not None:
            return semantic
        else:
            return {'type': 'text'}

    def render_html(self, pos, topic):
        semantic = self.get_field_semantic(pos)
        values = self.get_field_values(pos)
        if semantic['type'] == 'chart':
            content = f'<img src="chart{pos}.svg">'
        elif semantic['type'] == 'text':
            content = '<ol>' + ''.join([f'<li>{str(value)}</li>' for value in values if len(str(value)) > 0]) + '</ol>'
        else:
            raise ValueError(f'unknown semantic: {semantic["type"]}')
        return f"""
                <h6>{topic}</h6>
                <p class="field_title">{self.get_field_title(pos)}</p>
                {content}
            """

    def render_chart(self, pos, semantic):
        values = self.get_field_values(pos)
        frequencies, labels, colors = list(), list(), list()
        for legend_item in semantic['legend']:
            frequency = sum((str(value) == str(legend_item['key']) for value in values))
            if frequency == 0: continue
            frequencies.append(frequency)
            labels.append(legend_item['label'] + f' ({frequency})')
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


class Slides:

    def __init__(self, data, slides_filepath, csv_raw):
        self.data = data
        slides_dom = minidom.parse(slides_filepath).getElementsByTagName('slides')[0]
        self.title = slides_dom.attributes['title'].value
        self.slides = list()
        current_topic = ''
        for element in slides_dom.childNodes:
            if isinstance(element, minidom.Text): continue
            if element.tagName == 'slide':
                slide_template = string.Template(element.firstChild.data)
                self.slides.append({'type': 'raw', 'content': slide_template.substitute(dict(title=self.title, rows=len(data.rows), rawdata_url=csv_raw))})
            elif element.tagName == 'slide-sequence':
                for field in get_fields(element.attributes['fields'].value, len(self.data)):
                    if len(data.get_field_values(field)) == 0: continue
                    self.slides.append({'type': 'field', 'field': field, 'topic': current_topic})
            elif element.tagName == 'topic':
                current_topic = '' if element.firstChild is None else element.firstChild.data
                if len(current_topic) > 0 and (not element.hasAttribute('intro-slide') or element.attributes['intro-slide'].value != 'false'):
                    self.slides.append({'type': 'raw', 'content': f'<h1>{current_topic}</h1>'})

    def render_html(self):
        slides_html_list = list()
        for slide in self.slides:
            if slide['type'] == 'raw':
                slides_html_list.append(f'<section>{slide["content"]}</section>')
            elif slide['type'] == 'field':
                slides_html_list.append('<section>' + self.data.render_html(slide['field'], slide['topic']) + '</section>')
        return '\n'.join(slides_html_list)


if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('build_directory', type=str)
    parser.add_argument('--csv_input', type=str, default='data.csv')
    parser.add_argument('--csv_raw', type=str, default='data.csv', help='Name of the file used to deploy the raw CSV data.')
    parser.add_argument('--semantics', type=str, default='semantics.xml')
    parser.add_argument('--slides', type=str, default='slides.xml')
    args = parser.parse_args()
    
    data = Data(args.csv_input, args.semantics)
    slides = Slides(data, args.slides, args.csv_raw)
    
    with open('template.html') as fin:
        template = string.Template(fin.read())
    index_html = template.substitute(dict(title=slides.title, slides_html=slides.render_html()))
    
    print(f'Building into: {args.build_directory}')
    shutil.copy(args.csv_input, os.path.join(args.build_directory, args.csv_raw))
    os.chdir(args.build_directory)
    
    os.system('git init')
    os.system('git remote add origin https://github.com/hakimel/reveal.js')
    os.system('git fetch origin bddeb70f4ef18aca1e0e7a3feed3f7f91de9682f')
    os.system('git reset --hard FETCH_HEAD')
    
    with open('index.html', 'w') as fout:
        fout.write(index_html)

    data.render_charts()
