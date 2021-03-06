import os
import re
import httplib2
import json
import webapp2

from google.appengine.ext.webapp import template
from google.appengine.api import memcache

from apiclient.discovery import build
from apiclient import errors

from oauth2client import appengine

from config import *

_SCOPE = 'https://www.googleapis.com/auth/bigquery'

credentials = appengine.AppAssertionCredentials(scope=_SCOPE)
http = credentials.authorize(httplib2.Http())

# [tweets:2015_01_09]
FROM_CLAUSE = "[%s.%s]" % (DATASET_ID, TABLE_ID) 

REMOVE_HTML = re.compile(r'<.*?>')

def get_service():
    
    return build('bigquery', 'v2', http=http)

class ShowHome(webapp2.RequestHandler):
    
    def get(self):
        template_data = {}
        template_path = 'templates/index.html'
        self.response.out.write(template.render(template_path, template_data))

#         queryData = {'query':'SELECT SUM(word_count) as WCount,corpus_date,group_concat(corpus) as Work FROM '
#                      '[publicdata:samples.shakespeare] WHERE word="' + inputData + '" and corpus_date>0 GROUP BY corpus_date ORDER BY WCount'}

class Data(webapp2.RequestHandler):
    
    def get(self):
        
        source = self.request.get("source")
        pivot = self.request.get("pivot")
        charttype = self.request.get("charttype")
        terms = self.request.get("terms")
        if terms:
            terms = terms.lower().split(',')
            for idx, val in enumerate(terms):
                h = "'" + val + "'"
                terms[idx] = h
            terms = ','.join(terms) 

        query = None
        args = {}
        
        if source == 'sources':

            if pivot == 'hour' or charttype == 'timeseries':

                query = "SELECT source as source, HOUR(TIMESTAMP(created_at)) AS create_hour, count(*) as count FROM %s WHERE source contains 'Twitter for' GROUP by create_hour, source ORDER BY source ASC, create_hour ASC" % (FROM_CLAUSE)
                
                tableData = get_service().jobs()
                dataList = tableData.query(projectId=PROJECT_NUMBER, body={'query':query}).execute()
                
                # key: source, value: [source, d1, d2, d3...]
                buckets = {}
                columns = [['x', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23' ]]
                if 'rows' in dataList:
                    for row in dataList['rows']:
                        for key, dict_list in row.iteritems():
                            source = REMOVE_HTML.sub('', dict_list[0]['v'])
                            hour = int(dict_list[1]['v'])
                            count = int(dict_list[2]['v'])
                            
                            column = buckets.get(source, None)
                            if not column:
                                column = [0] * 25
                                column[0] = source
                                buckets[source] = column

                            column[hour + 1] = count
                else:
                    columns.append([])
                    
                for key, value in buckets.iteritems():
                    columns.append(value)

                # http://c3js.org/samples/simple_multiple.html
                # query and title are returned for display in UI
                args = {
                    'data' : {
                        'x' : 'x',
                        'columns' : columns 
                    },
                    'query' : query,
                    'title' : "Sources by hour" 
                }

            elif charttype == 'donut' or charttype == 'bar' or charttype == 'popular':
                
                query = "SELECT source as source, count(*) as count FROM %s GROUP by source ORDER BY count DESC LIMIT 20" % (FROM_CLAUSE)
        
                tableData = get_service().jobs()
                dataList = tableData.query(projectId=PROJECT_NUMBER, body={'query':query}).execute()
         
                columns = []
                if 'rows' in dataList:
                    for row in dataList['rows']:
                        for key, dict_list in row.iteritems():
                            source = REMOVE_HTML.sub('', dict_list[0]['v'])
                            count = int(dict_list[1]['v'])
                            columns.append([source, count])
                else:
                    columns.append([])

                # http://c3js.org/samples/chart_donut.html
                # query and title are returned for display in UI
                args = {
                    'data' : {
                        'columns' : columns,
                        'type' : charttype
                    },
                    'donut' : {
                        'title' : "Tweet sources"
                    },
                    'bar': {
                        'width': {
                            'ratio': 0.5 
                        }
                    },
                    'query' : query,
                    'title' : "Sources by type"
                }
                
            elif pivot == 'location' or charttype == 'map':

                pass
            
        elif source == 'hashtags' or source == 'mentions':

            object = None
            prefix = None
            col = None
            
            if source == 'hashtags':
                object = 'Hashtags'
                prefix = '#'
                col = 'entities.hashtags.text'
            elif source == 'mentions':
                object = 'User mentions'
                prefix = '@'
                col = 'entities.user_mentions.screen_name'

            if pivot == 'hour' or charttype == 'timeseries':

                query = """SELECT
                      LOWER(%s),
                      HOUR(TIMESTAMP(created_at)) AS create_hour,
                      COUNT(*) AS COUNT
                    FROM %s 
                    WHERE LOWER(%s) IN (%s)
                    GROUP BY create_hour, 1
                    ORDER BY 1, create_hour ASC""" % (col, FROM_CLAUSE, col, terms)
                
                tableData = get_service().jobs()
                dataList = tableData.query(projectId=PROJECT_NUMBER, body={'query':query}).execute()
                
                # key: source, value: [source, d1, d2, d3...]
                buckets = {}
                columns = [['x', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23' ]]
                if 'rows' in dataList:
                    for row in dataList['rows']:
                        for key, dict_list in row.iteritems():
                            source = prefix + REMOVE_HTML.sub('', dict_list[0]['v'])
                            hour = int(dict_list[1]['v'])
                            count = int(dict_list[2]['v'])
                            
                            column = buckets.get(source, None)
                            if not column:
                                column = [0] * 25
                                column[0] = source
                                buckets[source] = column

                            column[hour + 1] = count
                else:
                    columns.append([])
                    
                for key, value in buckets.iteritems():
                    columns.append(value)
                    
                # http://c3js.org/samples/simple_multiple.html
                # query and title are returned for display in UI
                args = {
                    'data' : {
                        'x' : 'x',
                        'columns' : columns 
                    },
                    'query' : query,
                    'title' : "%s by hour" % object
                }

            elif pivot == 'popular':

                query = "SELECT %s, count(*) as count FROM %s WHERE %s IS NOT NULL GROUP by %s ORDER BY count DESC LIMIT 10" % (col, FROM_CLAUSE, col, col)
                print query
        
                tableData = get_service().jobs()
                dataList = tableData.query(projectId=PROJECT_NUMBER, body={'query':query}).execute()
         
                columns = []
                if 'rows' in dataList:
                    for row in dataList['rows']:
                        for key, dict_list in row.iteritems():
                            source = prefix + dict_list[0]['v']
                            count = int(dict_list[1]['v'])
                            columns.append([source, count])
                else:
                    columns.append([])

                # http://c3js.org/samples/chart_donut.html
                # query and title are returned for display in UI
                # cheating by always adding donut/bar attributes
                args = {
                    'data' : {
                        'columns' : columns,
                        'type' : charttype
                    },
                    'donut' : {
                        'title' : "Hashtags"
                    },
                    'bar': {
                        'width': {
                            'ratio': 0.5 
                        }
                    },
                    'query' : query,
                    'title' : "%s by count" % object
                }

            elif charttype == 'donut' or charttype == 'bar':

                query = "SELECT %s, count(*) as count FROM %s WHERE LOWER(%s) in (%s) GROUP by %s ORDER BY count" % (col, FROM_CLAUSE, col, terms, col)
        
                tableData = get_service().jobs()
                dataList = tableData.query(projectId=PROJECT_NUMBER, body={'query':query}).execute()
         
                columns = []
                if 'rows' in dataList:
                    for row in dataList['rows']:
                        for key, dict_list in row.iteritems():
                            source = prefix + REMOVE_HTML.sub('', dict_list[0]['v'])
                            count = int(dict_list[1]['v'])
                            columns.append([source, count])
                else:
                    columns.append([])

                # http://c3js.org/samples/chart_donut.html
                # query and title are returned for display in UI
                # cheating by always adding donut/bar attributes
                args = {
                    'data' : {
                        'columns' : columns,
                        'type' : charttype
                    },
                    'donut' : {
                        'title' : "Hashtags"
                    },
                    'bar': {
                        'width': {
                            'ratio': 0.5 
                        }
                    },
                    'query' : query,
                    'title' : "%s by count" % object
                }
                
            elif pivot == 'location' or charttype == 'map':

                pass
            
        self.response.headers['Content-Type'] = 'application/json'
        self.response.out.write(json.dumps(args))

class Chart(webapp2.RequestHandler):
    
    def get(self):
        template_data = {}
        template_path = 'Templates/chart.html'
        self.response.out.write(template.render(template_path, template_data))

application = webapp2.WSGIApplication([
    ('/data', Data),
    ('/chart', Chart),
    ('/', Chart),
], debug=True)
