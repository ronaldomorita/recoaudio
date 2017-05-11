import warnings
import json
from dejavu import Dejavu
from dejavu.recognize import FileRecognizer

warnings.filterwarnings("ignore")
    
class AudioSegment:
    def __init__(self, file_name, start_position, end_position):
        self.file_name = file_name
        self.start_position = start_position
        self.end_position = end_position
        self.recognition_result = json.loads('{}')
        
    def set_recognition_result(self, result):
        self.recognition_result = json.loads(str(result).replace("'",'"'))
    
    def size(self):
        return self.end_position - self.start_position
    
    def contains_position(self, position):
        return position > self.start_position and  position < self.end_position

class AudioSegmentHandler:
    # Expected amount of time (in seconds) of the original audio record.
    total_time = 30
    
    # Maximum size (in seconds) of each segment (maybe less than max if it starts before the first postion or ends after the last one).
    max_segment_size = 8 
    
    # Start position of the first segment. The end position will be the first_segment_start_position + max_segment_size. 
    # If a segment starts in a position < 0, the start position will be 0 and the segment_size will be equal to the end position defined above.
    # The last position of a segment must be > 0, so the minimum value for first_segment_start_position is 1 - max_segment_size.
    first_segment_start_position = -2
    
    # Start position of the last segment. The end position will be the last_segment_start_position + max_segment_size. 
    # If a segment ends in a position > total_time, the end position will be total_time and the segment_size will equal to the total_time - last_segment_start_position.
    # The first position of a segment must be < total_time, so the maximum value for last_segment_start_position is total_time - 1.
    last_segment_start_position = 24
    
    # The amount of seconds between the start position of consecutive segmets
    segment_step = 2
    
    # Position of the inital checkpoint
    initial_checkpoint = 3
    
    # The amount of seconds between consecutive checkpoints
    checkpoint_step = 4
    
    def __init__(self, djv):
        self.djv = djv
        self.segment_list = []
        
    def generate_segments(self, filepath):
        path = filepath[0:filepath.rfind('/')+1]
        name = filepath[filepath.rfind('/')+1:]
        self.segment_list = []
        position = self.first_segment_start_position
        while position <= self.last_segment_start_position:
            end_position = position + self.max_segment_size
            actual_start_position = position if position >= 0 else 0
            actual_end_position = end_position if end_position <= self.total_time else self.total_time
            segment_filename = path + "_" + str(actual_start_position) + "_" + str(actual_end_position) + "_" + name
            self.djv.extract_audio_segment(filepath, segment_filename, actual_start_position, actual_end_position)
            self.segment_list.append( AudioSegment(segment_filename, actual_start_position, actual_end_position) )
            position += self.segment_step
        return self
    
    def recognize_segment_list(self):
        for s in self.segment_list:
            s.set_recognition_result(self.djv.recognize(FileRecognizer, s.file_name))
        return self
        
        
def recognize():
    # load config from a JSON file (or anything outputting a python dictionary)
    with open("dejavu.cnf.SAMPLE") as f:
        # create a Dejavu instance
        djv = Dejavu(json.load(f))

        # Recognize audio from a file
        pcmfilename = "records/recorded.pcm"
        wavfilename = "records/recorded_converted.wav"
        djv.convert_pcm_to_wav(pcmfilename, wavfilename)
        
        # cria a lista de segmentos e faz o reconhecimento de cada um
        handler = AudioSegmentHandler(djv).generate_segments(wavfilename).recognize_segment_list()
                
        #print "From file we recognized: %s\n" % segment_list
        return handler.segment_list
        
    return ['["unable to open config"]']
