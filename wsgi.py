# coding: utf-8
import ra_recognize
import ra_loadsamples
import json
from datetime import datetime
import cgi
from cgi import escape
import cgitb
import gzip
cgitb.enable()


CHARSET = 'UTF-8'

html_recognize_result = """
<!DOCTYPE html>
<head><META http-equiv="Content-Type" content="text/html; charset=UTF-8"></head>
<html>
<body style="margin: 0px;">
<!-- content-start -->
<div style="background-color:#EEEEAA">
  <h2>Detalhes do reconhecimento:</h2>
  <p style="padding-left: 6px">
    <b>Timestamp:</b> %(timestamp)s<br>
  </p>
%(checkpoints_content)s    
</div>
<!-- content-end -->
%(notification_content)s
</body>
</html>
"""

html_checkpoint = """
  <div style="background-color:%(checkpoint_color)s; width:98%%; margin-left: 1%%;">
      <b>No segundo %(checkpoint)s</b><br>
      <span style="color:#AA6600;"><b>Audio:</b> %(song_id)s: %(song_name)s</span><br>
      <b>Confianca media:</b> %(confidence)s<br>
      <b>resultado por segmento:</b>
      <table>
        <thead>
          <tr>
            <th>Trecho</th>
            <th style="color:#AA6600;">Audio</th>
            <th>Confianca</th.
          </tr>
        </thead>
        <tboby>
%(segments_content)s
        </tbody>
      </table>
      <br>
  </div>
"""

html_segment = """
          <tr>
            <td style="text-align: center;">%(file_info)s</td>
            <td style="text-align: center; color:#AA6600;">%(song_id)s: %(song_name)s</td>
            <td style="text-align: center;">%(confidence)s</td>
          </tr>
"""

html_notification = "<!-- notific: %(id)s|%(content)s notific-end -->\n"

html_sample_result = """
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


def timestamp_to_date(ts):
    return datetime.utcfromtimestamp(float(ts)/1000).strftime('%d/%m/%Y %H:%M:%S.%f')[:-3] if ts.isdigit() else ''

def save_history(ts, handler):
    conv_file_name = 'recorded_converted.wav'
    hist_file_name = ts+conv_file_name
    log_file_name = ts+conv_file_name.replace('.wav','.log')
    with open('records/'+conv_file_name, 'rb') as conv_file:
        with open('records/history/'+hist_file_name, 'wb') as hist_file:
            hist_file.write(conv_file.read())
            with open('records/history/'+log_file_name, 'w') as log_file:
                log_file.write('filename: %s\ntimestamp: %s (%s)\nrecognized info:\n'%(hist_file_name,timestamp_to_date(ts),ts))
                list_ckeckpoints_str = [cp.to_str_sum() for cp in handler.checkpoint_list]
                log_file.write('\n'.join(list_ckeckpoints_str))
                log_file.write('\n\n')
    
def populate_recognition_response_body(ts, handler):
    checkpoints_content = ""
    checkpoint_color = '#F8F8F8'
    for cp in handler.checkpoint_list:
        # prepare segment content
        segments_content = ''
        for s in cp.segments_analysed:
            segments_content += html_segment % {
                'file_info':    str(s.start_position) + 's a ' + str(s.end_position) + 's',
                'song_id':      str(s.recognition_result['song_id']),
                'song_name':    str(s.recognition_result['song_name']),
                'confidence':   str(s.recognition_result['confidence']),
            }
        checkpoints_content += html_checkpoint % {
            'checkpoint':       str(cp.checkpoint),
            'song_id':          str(cp.song_id),
            'song_name':        cp.song_name,
            'confidence':       str(cp.confidence_avg),
            'segments_content': segments_content,
            'checkpoint_color': checkpoint_color,
        }
        checkpoint_color = '#E8E8E8' if checkpoint_color == '#F8F8F8' else '#F8F8F8'
    
    notification_content = '\n'
    if handler.notification_list:
        for key in handler.notification_list.keys():
            notification_content += html_notification % {
                'id':           str(key),
                'content':      handler.notification_list[key],
            }
    
    # prepare response
    date_timestamp = timestamp_to_date(ts) if ts.isdigit else 'No timestamp'
    response_body = html_recognize_result % {
        'timestamp':            date_timestamp,
        'checkpoints_content':  checkpoints_content,
        'notification_content': notification_content,
    }
    return response_body.encode('utf-8')
    
def populate_sample_response_body(file_name,result):
    jresult = json.loads(result)
    separator = '</dd><dd>'
    textdefault = '<dd>Nenhum arquivo</dd>'
    converted_before     = '<dd>' + separator.join(f for f in jresult['converted_before']    ).encode('utf-8') + '</dd>' if jresult['converted_before']     else textdefault
    converted_now        = '<dd>' + separator.join(f for f in jresult['converted_now']       ).encode('utf-8') + '</dd>' if jresult['converted_now']        else textdefault
    fingerprinted_before = '<dd>' + separator.join(f for f in jresult['fingerprinted_before']).encode('utf-8') + '</dd>' if jresult['fingerprinted_before'] else textdefault
    fingerprinted_now    = '<dd>' + separator.join(f for f in jresult['fingerprinted_now']   ).encode('utf-8') + '</dd>' if jresult['fingerprinted_now']    else textdefault
    response_body = html_sample_result % {
        'file_name':            file_name,
        'converted_before':     converted_before,
        'converted_now':        converted_now,
        'fingerprinted_before': fingerprinted_before,
        'fingerprinted_now':    fingerprinted_now,
    }
    return response_body
   
    
def application(environ, start_response):
    uri_path = environ['RAW_URI']
    
    response_body = 'NOTHING TO DO'
    content_type = 'text/plain'
    
    if uri_path == '/':
        # get recorded file form POST
        form = cgi.FieldStorage(fp=environ['wsgi.input'], environ=environ)
        file_name = 'No recorded file uploaded' if form else 'No form found'
        ts = ''
        if 'recorded' in form:
            ts = cgi.escape(form.getvalue('ts',''))
            post_file = form['recorded']
            if post_file.filename:
                file_name = cgi.escape(post_file.filename)
                # save recorded file to filesystem
                with open('records/'+file_name, 'wb') as local_file:
                    local_file.write(post_file.file.read())
                if file_name.endswith('.gz'):
                    with gzip.open('records/'+file_name, 'rb') as zip_file:
                        with open('records/'+file_name.rstrip('.gz'), 'wb') as unzip_file:
                            unzip_file.write(zip_file.read())
            
        # recognize recorded file
        handler = ra_recognize.recognize()
        
        # save history
        save_history(ts, handler) if ts.isdigit() else None
        
        # prepare checkpoint content
        response_body = populate_recognition_response_body(ts, handler)
        content_type = 'text/html'
        
    elif uri_path == '/loadsample':
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
                if file_name.endswith('.gz'):
                    with gzip.open('references/'+file_name, 'rb') as zip_file:
                        with open('references/'+file_name.rstrip('.gz'), 'wb') as unzip_file:
                            unzip_file.write(zip_file.read())
            
        # recognize sample file
        result = ra_loadsamples.load()
        
        # prepare response
        response_body = populate_sample_response_body(file_name, result)
        content_type = 'text/html'
    
    elif uri_path == '/loadoffers':
        # retrieve keyword offers
        response_body = ra_recognize.load_keyword_offers()
        content_type = 'application/json'
     
    start_response('200 OK', [('Content-Type', content_type+'; charset='+CHARSET),('Content-Length', str(len(response_body)))])
    return [response_body]
