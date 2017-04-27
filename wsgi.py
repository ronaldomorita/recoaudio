import ra_recognize
def application(env, start_response):
    start_response('200 OK', [('Content-Type', 'text/html')])
    song = ra_recognize.recognize()
    return_value = 'Hello RecoAudio!<br>' + str(song)
    return [return_value]
