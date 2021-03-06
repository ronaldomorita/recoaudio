# coding: utf-8
import warnings
import simplejson as json
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
        self.recognition_result = json.loads(json.dumps(result))
    
    def size(self):
        return self.end_position - self.start_position
    
    def contains_position(self, position):
        return position > self.start_position and position < self.end_position
    
    def to_str(self):
        return "From %s to %s seconds and file %s, got song id %s, song name %s, confidence %s" %(
            str(self.start_position), str(self.end_position), self.file_name,
            str(self.recognition_result['song_id']), str(self.recognition_result['song_name'].encode('utf-8')), 
            str(self.recognition_result['confidence']))
    
    def to_str_sum(self):
        return "%s (%s), from %s to %s seconds" %(
            str(self.recognition_result['song_name'].encode('utf-8')), str(self.recognition_result['confidence']), 
            str(self.start_position), str(self.end_position))

        
class CheckpointResult:
    def __init__(self, checkpoint, song_id, song_name, confidence_avg, segments_analysed):
        self.checkpoint = checkpoint
        self.song_id = song_id
        self.song_name = song_name
        self.confidence_avg = confidence_avg
        self.segments_analysed = segments_analysed
        
    def get_sorted_segments_analysed(self):
        sorted_by_confidence = sorted(self.segments_analysed, key=lambda seg: seg.recognition_result['confidence'], reverse=True)
        sorted_list = [s for s in sorted_by_confidence if int(s.recognition_result['song_id']) == self.song_id]
        sorted_list.extend([s for s in sorted_by_confidence if int(s.recognition_result['song_id']) != self.song_id])
        return sorted_list
        
    def to_str(self):
        list_segments_analysed = [s.to_str() for s in self.get_sorted_segments_analysed()]
        return "At second %s, got song id %s, song name %s, confidence average %s\n    Segments analysed to get this result:\n    %s" %(
            str(self.checkpoint), str(self.song_id), self.song_name, str(self.confidence_avg), '\n    '.join(list_segments_analysed))
        
    def to_str_sum(self):
        list_segments_analysed = [s.to_str_sum() for s in self.get_sorted_segments_analysed()]
        return "At second %s, %s (%s)\n    %s" %(
            str(self.checkpoint), self.song_name, str(self.confidence_avg), '\n    '.join(list_segments_analysed))

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
    first_checkpoint = 3
    
    # The amount of seconds between consecutive checkpoints
    checkpoint_step = 4
    
    def __init__(self, djv):
        self.djv = djv
        self.segment_list = []
        self.checkpoint_list = []
        self.notification_list = {}
        self.offers_base = {}
        self.song_offers_base = {}
        song_offers = self.djv.load_song_offers()
        for so in song_offers:
            self.offers_base[so['offer_id']] = so['offer_content'].encode('utf-8')
            self.song_offers_base[so['song_id']] = so['offer_id']
        
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
    
    def compute_checkpoits(self):
        checkpoint = self.first_checkpoint
        while checkpoint <= self.total_time:
            cp_segments = [s for s in self.segment_list if s.contains_position(checkpoint)]
            cp_results = {}
            max_confidence = 0
            for seg in cp_segments:
                key = str(seg.recognition_result['song_id'])+'_'+seg.recognition_result['song_name'].encode('utf-8')
                value = cp_results[key] + seg.recognition_result['confidence'] if cp_results.has_key(key) else seg.recognition_result['confidence']
                cp_results[key] = value
                max_confidence = value if value > max_confidence else max_confidence
            if max_confidence:
                for key in cp_results.keys():
                    if cp_results[key] == max_confidence:
                        song_id = int(key[0:key.find('_')])
                        song_name = key[key.find('_')+1:]
                        self.checkpoint_list.append(CheckpointResult(
                            checkpoint, song_id, song_name,
                            max_confidence/(len(cp_segments)*1.0), cp_segments))
                        if self.song_offers_base.has_key(song_id) and max_confidence >= 3.0:
                            nofitication_id = self.song_offers_base[song_id]
                            self.notification_list[nofitication_id] = self.offers_base[nofitication_id] 
                        break;
            checkpoint += self.checkpoint_step
        return self

class KeywordOffer:
    
    OFFER_TEXT = '{"keywords": [%s],"content": "%s","offer_id": %s}'
    
    KEYWORDS_TEXT = '[%s],'
    
    SYNONYMS_TEXT = '"%s",'
    
    def __init__(self,offer_id,offer_content):
        self.offer_id = offer_id
        self.offer_content = offer_content
        self.keywords = {}
    
    def append_synonym(self,keyword_id,keyword_synonym):
        if not self.keywords.has_key(keyword_id):
            self.keywords[keyword_id] = []
        if keyword_synonym not in self.keywords[keyword_id]:
            self.keywords[keyword_id].append(keyword_synonym)
            
    def to_json_str(self):
        keywords_str = '';
        for k in self.keywords.values():
            synonyms_str = '';
            for s in k:
                synonyms_str += self.SYNONYMS_TEXT %(s)
            if synonyms_str:
                keywords_str += self.KEYWORDS_TEXT %(synonyms_str[0:-1])
        return self.OFFER_TEXT %(keywords_str[0:-1], self.offer_content, str(self.offer_id)) if keywords_str else '{}'
       
        
def recognize():
    # load config from a JSON file (or anything outputting a python dictionary)
    with open("dejavu.cnf.SAMPLE") as f:
        # create a Dejavu instance
        djv = Dejavu(json.load(f))

        # Recognize audio from a file
        pcmfilename = "records/recorded.pcm"
        wavfilename = "records/recorded_converted.wav"
        djv.convert_pcm_to_wav(pcmfilename, wavfilename)
        
        # generate audio segments, recognize each segment and define the most probable audio for each checkpoint
        handler = AudioSegmentHandler(djv).generate_segments(wavfilename).recognize_segment_list().compute_checkpoits()
                
        return handler
        
    return AudioSegmentHandler(None)

def load_keyword_offers():
    keyword_offers = {};
    with open("dejavu.cnf.SAMPLE") as f:
        # create a Dejavu instance
        djv = Dejavu(json.load(f))
        
        resultset = djv.load_keyword_offers();
        for row in resultset:
            offer_id = row['offer_id']
            if not keyword_offers.has_key(offer_id):
                keyword_offers[offer_id] = KeywordOffer(offer_id,row['offer_content'].encode('utf-8'))
            keyword_offers[offer_id].append_synonym(row['offer_keyword_id'],row['keyword_synonym_value'].encode('utf-8'))
            
    offers_list = [ko.to_json_str() for ko in keyword_offers.values()]
    return '[' + ','.join(offers_list) +']'
    
