#!/usr/bin/env python
# coding: utf-8
import random
import splunklib.client as client
import splunklib.results as results

options={
    'host':         'localhost',
    'port':         8089,
    'auth_token':   'eyJraWQiOiJzcGx1bmsuc2VjcmV0IiwiYWxnIjoiSFM1MTIiLCJ2ZXIiOiJ2MiIsInR0eXAiOiJzdGF0aWMifQ.eyJpc3MiOiJhZG1pbiBmcm9tIEMwMkcyMzVCTUQ2UiIsInN1YiI6ImFkbWluIiwiYXVkIjoicHl0aG9uIHRlc3RzIiwiaWRwIjoiU3BsdW5rIiwianRpIjoiYWIyMzQ4M2FhYjk2OTA1ZGJmNGUwZTdlM2Y0OGI1MjE1ODcyOTUwM2ZmNjE0YjVjNzc5MWUyZWRlOGFkZjBhNSIsImlhdCI6MTY2Mzc4MDc3MiwiZXhwIjoxNzE1NjIwNzcyLCJuYnIiOjE2NjM3ODA3NzJ9.b0SRVIBCn3mEy3kXuE5BXyrNruW392Sch52QzWeCQ2n5NukW3dkT8FdH_YvQNwAr1DdP7JUROgdHdhCu2cT18A',
    'job_inspector_url_base': 'http://localhost:8000/en-US/manager/search/job_inspector?sid='
        }

service = client.connect(
    host=options["host"],
    port=options["port"],
    splunkToken=options["auth_token"],
    autologin=True)

def search_export(service_in,search_in,preview_in):

    search_id=str(round(random.uniform(10000000, 90000000),4))
    kwargs_export = {"search_mode": "normal",
                    "output_mode": "json",
                    "count":0,
                    "preview":preview_in,
                    "id":search_id}

    job = service_in.jobs.export(search_in, **kwargs_export)
    reader = results.JSONResultsReader(job)
    print(search_in)
    print("search id: {sid}, result count: {count}, preview: {preview}".format(sid=search_id,count=len(list(reader)),preview=preview_in))
    print(format_job_inspector(search_id))
    print("\n")

def format_job_inspector(sid_in):
    return options["job_inspector_url_base"]+str(sid_in)

def format_search(search_in,event_count_in):
    search=search_in.format(event_count=event_count_in)
    return search

# optimizer bug would have been really bad
# search_string="search index=_internal | head {event_count} | table * | noop search_optimization=false"
search_string="search index=_internal | head {event_count} | table * "

search_export(service,format_search(search_string,1000),"true")
search_export(service,format_search(search_string,1000),"false")
search_export(service,format_search(search_string,200000),"true")
search_export(service,format_search(search_string,200000),"false")

# search_string="search index=_internal | head {event_count} | table _time"

service.logout()