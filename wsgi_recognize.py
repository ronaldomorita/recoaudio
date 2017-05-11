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
<!-- content-start -->
<div style="background-color:#EEEEAA">
    <h2>Detalhes do reconhecimento:</h2>
    <p>
        Timestamp: %(timestamp)s<br>
    </p>
%(file_content)s    
</div>
<!-- content-end -->
</body>
</html>
"""

html_audio = """
    <p>
        File: %(file_info)s<br>
        ID do áudio: %(song_id)s<br>
        Nome do áudio: %(song_name)s<br>
        Nível de confiança: %(confidence)s<br>
    </p>
"""

def application(environ, start_response):
    # get recorded file form POST
    form = cgi.FieldStorage(fp=environ['wsgi.input'], environ=environ)
    timestamp = '' if form else 'No form found'
    file_name = 'No recorded file uploaded' if form else 'No form found'
    ts = ''
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
    segments = ra_recognize.recognize()
    
    # save history
    if ts.isdigit():
        conv_file_name = 'recorded_converted.wav'
        hist_file_name = ts+conv_file_name
        log_file_name = ts+conv_file_name.replace('.wav','.log')
        with open('records/'+conv_file_name, 'rb') as conv_file:
            with open('records/history/'+hist_file_name, 'wb') as hist_file:
                hist_file.write(conv_file.read())
                with open('records/history/'+log_file_name, 'w') as log_file:
                    log_file.write('filename: '+hist_file_name+'\ntimestamp: '+timestamp+' ('+ts+')\nrecognized info: '+song)
    
    # prepare file content
    file_content = ""
    for s in segments:
        file_content += html_audio % {
            'file_info':      s.file_name + ' ' + str(s.start_position) + ' ' + str(s.end_position),
            'song_id':        str(s.recognition_result['song_id']),
            'song_name':      str(s.recognition_result['song_name']),
            'confidence':     str(s.recognition_result['confidence']),
        }
    
    # prepare response
    response_body = html % {
        'timestamp':      timestamp,
        'file_content':   file_content,
    }
    #else:
    #    response_body = html % {
    #        'timestamp':      timestamp,
    #        'song_id':        ' - ',
    #        'song_name':      'ÁUDIO NÃO ENCONTRADO',
    #        'file_sha1':      ' - ',
    #        'confidence':     ' - ',
    #        'offset_seconds': ' - ',
    #        'match_time':     ' - ',
    #        'offset':         ' - ',
    #    }
        
    start_response('200 OK', [('Content-Type', 'text/html; charset=UTF-8'),('Content-Length', str(len(response_body)))])
    return [response_body]
