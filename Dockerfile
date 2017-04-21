FROM heroku/miniconda

# Grab requirements.txt.
ADD ./requirements.txt /tmp/requirements.txt

# Install dependencies
RUN pip install -qr /tmp/requirements.txt

# Add our code
ADD ./ /opt/recoaudio/
WORKDIR /opt/recoaudio

RUN conda install portaudio numpy scipy matplotlib tk

#CMD gunicorn --bind 0.0.0.0:$PORT wsgi
CMD gunicorn --bind 0.0.0.0:$PORT recoaudio.wsgi --log-file -