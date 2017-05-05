import warnings
import json
from dejavu import Dejavu

warnings.filterwarnings("ignore")

def load():
    # load config from a JSON file (or anything outputting a python dictionary)
    with open("dejavu.cnf.SAMPLE") as f:
        config = json.load(f)

        # create a Dejavu instance
        djv = Dejavu(config)

        # Fingerprint all recorded files in the directory we saved it
        convertion = djv.convert_pcm_to_wav_directory("references")
        fingerprint = djv.fingerprint_directory("references", [".wav"])
        
        result = convertion[:-1] + ',' + fingerprint[1:]
        #print result
        return result
        
    return '["unable to open config"]'

