#!/usr/bin/env python3
"""Comprobaciones HTTP contra el servidor propio iniciado; sin búsqueda externa."""
import http.client
import json
import argparse

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--port', type=int, default=8765)
args = parser.parse_args()


def request(path, expected=200, method="GET", body=None, headers=None):
    connection = http.client.HTTPConnection("127.0.0.1",args.port,timeout=10)
    connection.request(method,path,body=body,headers=headers or {})
    response=connection.getresponse()
    raw=response.read()
    assert response.status==expected, (path,response.status,raw[:200])
    assert response.getheader('X-Content-Type-Options')=='nosniff'
    connection.close()
    return raw


html=request('/').decode()
assert '<html lang="es">' in html
catalog=json.loads(request('/api/catalog'))
assert len(catalog['topics'])==9 and len(catalog['references'])==10
assert all(reference.get('review_access') for reference in catalog['references'].values())
assert all(reference.get('quartile_details', {}).get('metric_year') == 2023 for reference in catalog['references'].values() if reference.get('quartile_details'))
assert all(reference.get('quartile_details') or reference['quartile'] == 'cuartil no verificado' for reference in catalog['references'].values())
for path in ('/server.py','/.agents/skills/biomarcadores-ux/SKILL.md','/.cache/evidence.json','/../AGENTS.md','/%2e%2e/AGENTS.md'):
    request(path,404)
request('/',403,headers={'Host':'evil.example'})
request('/api/catalog',403,headers={'Origin':'https://evil.example'})
request('/api/search?q=x',400)
request('/api/refresh',403,'POST',body='{}',headers={'Content-Type':'application/json'})
request('/api/refresh',400,'POST',body='{"q":42}',headers={'Content-Type':'application/json','X-Local-Request':'1'})
request('/api/refresh',400,'POST',body='invalid',headers={'Content-Type':'application/json','X-Local-Request':'1'})
print('13 comprobaciones HTTP correctas: recursos locales, biblioteca, rutas privadas, Host, Origin y validación de entradas.')
