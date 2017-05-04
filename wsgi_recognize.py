# coding: utf-8
import ra_recognize
import json
import cgi
import cgitb
cgitb.enable()

html = """
<html>
<body>
    <h2>Detalhes do reconhecimento:</h2>
    <p>Arquivo de upload: %(file_name)s</p>
    <p>
        ID do áudio: %(song_id)s<br>
        Nome do áudio: %(song_name)s<br>
        file_sha1: %(file_sha1)s<br>
        Nível de confiança: %(confidence)s<br>
        offset (em segundos): %(offset_seconds)s<br>
        tempo para reconhecimento: %(match_time)s<br>
        offset: %(offset)s<br>
    </p>
    <p>Original info: %(song)s</p>
</body>
</html>
"""

def application(env, start_response):
    #response_body = 'Hello RecoAudio!<br>' + str(song)
    
    ###POST###
    form = cgi.FieldStorage(fp=env['wsgi.input'], environ=env)
    file_name = 'There\'s a form' if form else 'No file uploaded'
    if "recorded" in form:
        fileitem = form["recorded"]
        file_name = fileitem.filename or file_name
        
    # the environment variable CONTENT_LENGTH may be empty or missing
    #try:
    #    request_body_size = int(env.get('CONTENT_LENGTH', 0))
    #except (ValueError):
    #    request_body_size = 0

    # When the method is POST the variable will be sent
    # in the HTTP request body which is passed by the WSGI server
    # in the file like wsgi.input environment variable.
    #request_body = env['wsgi.input'].read(request_body_size)
    #d = parse_qs(request_body)
    ###POST###

    ###GET###
    # Returns a dictionary in which the values are lists
    #d = parse_qs(env['QUERY_STRING'])
    ###GET###

    # As there can be more than one value for a variable then
    # a list is provided as a default value.
    #age = d.get('age', [''])[0] # Returns the first age value
    #hobbies = d.get('hobbies', []) # Returns a list of hobbies

    # Always escape user input to avoid script injection
    #age = escape(age)
    #hobbies = [escape(hobby) for hobby in hobbies]

    song = ra_recognize.recognize()
    jsong = json.loads(str(song).replace("'",'"'))
    
    response_body = html % { # Fill the above html template in
        'file_name':      file_name,
        'song_id':        str(jsong['song_id']        or 'Empty'),
        'song_name':      str(jsong['song_name']      or 'Empty'),
        'file_sha1':      str(jsong['file_sha1']      or 'Empty'),
        'confidence':     str(jsong['confidence']     or 'Empty'),
        'offset_seconds': str(jsong['offset_seconds'] or 'Empty'),
        'match_time':     str(jsong['match_time']     or 'Empty'),
        'offset':         str(jsong['offset']         or 'Empty'),
        'song':           song or 'Empty',
    }

    start_response('200 OK', [('Content-Type', 'text/html'),('Content-Length', str(len(response_body))),('charset','utf-8')])
    return [response_body]
