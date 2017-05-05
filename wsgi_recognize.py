# coding: utf-8
import ra_recognize
import json
from datetime import datetime
import cgi
from cgi import escape
import cgitb
cgitb.enable()

html = """
<!DOCTYPE html>
<head><META http-equiv="Content-Type" content="text/html; charset=UTF-8"></head>
<html>
<body>
    <h2>Detalhes do reconhecimento:</h2>
    <p>
        Timestamp: %(timestamp)s<br>
        Arquivo de upload: %(file_name)s<br>
    </p>
    <p>
        ID do áudio: %(song_id)s<br>
        Nome do áudio: %(song_name)s<br>
        file_sha1: %(file_sha1)s<br>
        Nível de confiança: %(confidence)s<br>
        offset (em segundos): %(offset_seconds)s<br>
        tempo para reconhecimento: %(match_time)s<br>
        offset: %(offset)s<br>
    </p>
</body>
</html>
"""

def application(environ, start_response):
    # get recorded file form POST
    form = cgi.FieldStorage(fp=environ['wsgi.input'], environ=environ)
    timestamp = '' if form else 'No form found'
    file_name = 'No recorded file uploaded' if form else 'No form found'
    if 'recorded' in form:
        ts = cgi.escape(form.getvalue('ts',''))
        timestamp = datetime.utcfromtimestamp(float(ts)/1000).strftime('%d/%m/%Y %H:%M:%S.%f')[:-3] if ts.isdigit() else timestamp
        post_file = form['recorded']
        if post_file.filename:
            file_name = cgi.escape(post_file.filename)
            # save recorded file to filesystem
            with open('records/'+file_name, 'wb') as local_file:
                local_file.write(post_file.file.read())
        
    # recognize recorded file
    song = ra_recognize.recognize()
    jsong = json.loads(str(song).replace("'",'"'))
    
    # prepare response
    response_body = html % {
        'timestamp':      timestamp,
        'file_name':      file_name,
        'song_id':        str(jsong['song_id']        or 'Empty'),
        'song_name':      str(jsong['song_name']      or 'Empty'),
        'file_sha1':      str(jsong['file_sha1']      or 'Empty'),
        'confidence':     str(jsong['confidence']     or 'Empty'),
        'offset_seconds': str(jsong['offset_seconds'] or 'Empty'),
        'match_time':     str(jsong['match_time']     or 'Empty'),
        'offset':         str(jsong['offset']         or 'Empty'),
    }
    start_response('200 OK', [('Content-Type', 'text/html; charset=UTF-8'),('Content-Length', str(len(response_body)))])
    return [response_body]
