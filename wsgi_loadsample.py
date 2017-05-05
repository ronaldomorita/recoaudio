# coding: utf-8
import ra_loadsamples
import json
import cgi
from cgi import escape
import cgitb
cgitb.enable()

html = """
<!DOCTYPE html>
<head><META http-equiv="Content-Type" content="text/html; charset=UTF-8"></head>
<html>
<body>
    <h2>Arquivando amostra na base:</h2>
    <p>
        <b>Arquivo de upload:</b> %(file_name)s<br>
    </p>
    <p>
        <h3>Status da geração de fingerprints:</h3>
        <dl>
            <dt><b>Convertidos anteriormente em .wav:</b></dt>
%(converted_before)s
            <dt><b>Convertidos agora em .wav:</b></dt>
%(converted_now)s
            <dt><b>Fingerprints gerados anteriormente:</b></dt>
%(fingerprinted_before)s
            <dt><b>Fingerprints gerados agora:</b></dt>
%(fingerprinted_now)s
        </dl>
    </p>
</body>
</html>
"""

def application(environ, start_response):
    # get sample file form POST
    form = cgi.FieldStorage(fp=environ['wsgi.input'], environ=environ)
    file_name = 'No sample file uploaded' if form else 'No form found'
    if 'sample' in form:
        post_file = form['sample']
        if post_file.filename:
            file_name = cgi.escape(post_file.filename)
            # save sample file to filesystem
            with open('references/'+file_name, 'wb') as local_file:
                local_file.write(post_file.file.read())
        
    # recognize sample file
    result = ra_loadsamples.load()
    jresult = json.loads(result)
    
    # prepare response
    separator = '</dd><dd>'
    textdefault = '<dd>Nenhum arquivo</dd>'
    converted_before     = '<dd>' + separator.join(f for f in jresult['converted_before']    ).encode('utf-8') + '</dd>' if jresult['converted_before']     else textdefault
    converted_now        = '<dd>' + separator.join(f for f in jresult['converted_now']       ).encode('utf-8') + '</dd>' if jresult['converted_now']        else textdefault
    fingerprinted_before = '<dd>' + separator.join(f for f in jresult['fingerprinted_before']).encode('utf-8') + '</dd>' if jresult['fingerprinted_before'] else textdefault
    fingerprinted_now    = '<dd>' + separator.join(f for f in jresult['fingerprinted_now']   ).encode('utf-8') + '</dd>' if jresult['fingerprinted_now']    else textdefault
    response_body = html % {
        'file_name':            file_name,
        'converted_before':     converted_before,
        'converted_now':        converted_now,
        'fingerprinted_before': fingerprinted_before,
        'fingerprinted_now':    fingerprinted_now,
    }
    start_response('200 OK', [('Content-Type', 'text/html; charset=UTF-8'),('Content-Length', str(len(response_body)))])
    return [response_body]
