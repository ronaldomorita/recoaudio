# coding: utf-8
import ra_recognize
import json
from datetime import datetime
import cgi
from cgi import escape
import cgitb
import gzip
cgitb.enable()

html = """
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
    
def populate_response_body(ts, handler):
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
    
    # prepare response
    date_timestamp = timestamp_to_date(ts) if ts.isdigit else 'No timestamp'
    response_body = html % {
        'timestamp':            date_timestamp,
        'checkpoints_content':  checkpoints_content,
    }
    return response_body.encode('utf-8')
   
    
def application(environ, start_response):
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
    response_body = populate_response_body(ts, handler)
    
    start_response('200 OK', [('Content-Type', 'text/html; charset=UTF-8'),('Content-Length', str(len(response_body)))])
    return [response_body]
