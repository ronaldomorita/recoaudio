import warnings
import json
warnings.filterwarnings("ignore")

from dejavu import Dejavu
from dejavu.recognize import FileRecognizer, MicrophoneRecognizer

# load config from a JSON file (or anything outputting a python dictionary)
with open("dejavu.cnf.SAMPLE") as f:
    config = json.load(f)

if __name__ == '__main__':

    # create a Dejavu instance
    djv = Dejavu(config)

    # Recognize audio from a file
    pcmfilename = "records/recorded.pcm"
    wavfilename = "records/recorded_converted.wav"
    djv.convert_pcm_to_wav(pcmfilename, wavfilename)
    song = djv.recognize(FileRecognizer, wavfilename)
    print "From file we recognized: %s\n" % song
