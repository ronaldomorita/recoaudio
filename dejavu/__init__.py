from dejavu.database import get_database, Database
import dejavu.decoder as decoder
import fingerprint
import multiprocessing
import os
import traceback
import sys
import wave
import subprocess


class Dejavu(object):

    SONG_ID = "song_id"
    SONG_NAME = 'song_name'
    CONFIDENCE = 'confidence'
    MATCH_TIME = 'match_time'
    OFFSET = 'offset'
    OFFSET_SECS = 'offset_seconds'

    def __init__(self, config):
        super(Dejavu, self).__init__()

        self.config = config

        # initialize db
        db_cls = get_database(config.get("database_type", None))

        self.db = db_cls(**config.get("database", {}))
        self.db.setup()

        # if we should limit seconds fingerprinted,
        # None|-1 means use entire track
        self.limit = self.config.get("fingerprint_limit", None)
        if self.limit == -1:  # for JSON compatibility
            self.limit = None
        self.get_fingerprinted_songs()

    def get_fingerprinted_songs(self):
        # get songs previously indexed
        self.songs = self.db.get_songs()
        self.songhashes_set = set()  # to know which ones we've computed before
        for song in self.songs:
            song_hash = song[Database.FIELD_FILE_SHA1]
            self.songhashes_set.add(song_hash)

    def convert_pcm_to_wav(self, pcmfilename, wavfilename):
        with open(os.devnull, 'w') as devnull:
            subprocess.check_call(['ffmpeg', '-y', '-f', 's16le', '-ar', '44.1k', '-ac', '1', '-i', pcmfilename, wavfilename], stdout=devnull, stderr=subprocess.STDOUT)

    def convert_pcm_to_wav_directory(self, path):
        filenames_already_converted = []
        filenames_to_convert = []
        
        for pcmfilename, _ in decoder.find_files(path, ['.pcm']):
            wavfilename = pcmfilename.replace('.pcm','.wav')
            if os.path.exists(wavfilename):
                #print "%s already converted, continuing..." % pcmfilename
                filenames_already_converted.append(pcmfilename)
                continue
            self.convert_pcm_to_wav(pcmfilename, wavfilename)
            filenames_to_convert.append(pcmfilename)
        
        converted_before = ('"' + '","'.join(filenames_already_converted) + '"').replace(path+'/','') if filenames_already_converted else ''
        converted_now    = ('"' + '","'.join(filenames_to_convert) + '"').replace(path+'/','')        if filenames_to_convert        else ''
        return '{"converted_before":[' + converted_before + '],"converted_now":[' + converted_now + ']}'

    def extract_audio_segment(self, input_filename, output_filename, start_second, end_second):
        with open(os.devnull, 'w') as devnull:
            subprocess.check_call(['ffmpeg', '-y', '-i', input_filename, '-ss', str(start_second), '-to', str(end_second), output_filename], stdout=devnull, stderr=subprocess.STDOUT)
        
    def fingerprint_directory(self, path, extensions, nprocesses=None):
        # Try to use the maximum amount of processes if not given.
        try:
            nprocesses = nprocesses or multiprocessing.cpu_count()
        except NotImplementedError:
            nprocesses = 1
        else:
            nprocesses = 1 if nprocesses <= 0 else nprocesses

        pool = multiprocessing.Pool(nprocesses)

        filenames_already_fingerprinted = []
        filenames_to_fingerprint = []
        
        for filename, _ in decoder.find_files(path, extensions):
            # don't refingerprint already fingerprinted files
            if decoder.unique_hash(filename) in self.songhashes_set:
                #print "%s already fingerprinted, continuing..." % filename
                filenames_already_fingerprinted.append(filename)
                continue
            filenames_to_fingerprint.append(filename)

        # Prepare _fingerprint_worker input
        worker_input = zip(filenames_to_fingerprint,
                           [self.limit] * len(filenames_to_fingerprint))

        # Send off our tasks
        iterator = pool.imap_unordered(_fingerprint_worker,
                                       worker_input)

        # Loop till we have all of them
        while True:
            try:
                song_name, hashes, file_hash = iterator.next()
            except multiprocessing.TimeoutError:
                continue
            except StopIteration:
                break
            except:
                print("Failed fingerprinting")
                # Print traceback because we can't reraise it here
                traceback.print_exc(file=sys.stdout)
            else:
                sid = self.db.insert_song(song_name, file_hash)

                self.db.insert_hashes(sid, hashes)
                self.db.set_song_fingerprinted(sid)
                self.get_fingerprinted_songs()

        pool.close()
        pool.join()
        
        fingerprinted_before = ('"' + '","'.join(filenames_already_fingerprinted) + '"').replace(path+'/','') if filenames_already_fingerprinted else ''
        fingerprinted_now    = ('"' + '","'.join(filenames_to_fingerprint) + '"').replace(path+'/','')        if filenames_to_fingerprint        else ''
        return '{"fingerprinted_before":[' + fingerprinted_before + '],"fingerprinted_now":[' + fingerprinted_now + ']}'

    def fingerprint_file(self, filepath, song_name=None):
        songname = decoder.path_to_songname(filepath)
        song_hash = decoder.unique_hash(filepath)
        song_name = song_name or songname
        # don't refingerprint already fingerprinted files
        if song_hash in self.songhashes_set:
            print "%s already fingerprinted, continuing..." % song_name
        else:
            song_name, hashes, file_hash = _fingerprint_worker(
                filepath,
                self.limit,
                song_name=song_name
            )
            sid = self.db.insert_song(song_name, file_hash)

            self.db.insert_hashes(sid, hashes)
            self.db.set_song_fingerprinted(sid)
            self.get_fingerprinted_songs()

    def find_matches(self, samples, Fs=fingerprint.DEFAULT_FS):
        hashes = fingerprint.fingerprint(samples, Fs=Fs)
        return self.db.return_matches(hashes)

    def align_matches(self, matches):
        """
            Finds hash matches that align in time with other matches and finds
            consensus about which hashes are "true" signal from the audio.

            Returns a dictionary with match information.
        """
        # align by diffs
        diff_counter = {}
        largest = 0
        largest_count = 0
        song_id = -1
        for tup in matches:
            sid, diff = tup
            if diff not in diff_counter:
                diff_counter[diff] = {}
            if sid not in diff_counter[diff]:
                diff_counter[diff][sid] = 0
            diff_counter[diff][sid] += 1

            if diff_counter[diff][sid] > largest_count:
                largest = diff
                largest_count = diff_counter[diff][sid]
                song_id = sid

        # extract idenfication
        song = self.db.get_song_by_id(song_id)
        if song:
            # TODO: Clarify what `get_song_by_id` should return.
            songname = song.get(Dejavu.SONG_NAME, None)
        else:
            return None

        # return match info
        nseconds = round(float(largest) / fingerprint.DEFAULT_FS *
                         fingerprint.DEFAULT_WINDOW_SIZE *
                         fingerprint.DEFAULT_OVERLAP_RATIO, 5)
        song = {
            Dejavu.SONG_ID : song_id,
            Dejavu.SONG_NAME : songname,
            Dejavu.CONFIDENCE : largest_count,
            Dejavu.OFFSET : int(largest),
            Dejavu.OFFSET_SECS : nseconds,
            Database.FIELD_FILE_SHA1 : song.get(Database.FIELD_FILE_SHA1, None),}
        return song

    def recognize(self, recognizer, *options, **kwoptions):
        r = recognizer(self)
        return r.recognize(*options, **kwoptions)
        
    def load_song_offers(self):
        return self.db.get_song_offers()

    def load_keyword_offers(self):
        return self.db.get_keyword_offers()


def _fingerprint_worker(filename, limit=None, song_name=None):
    # Pool.imap sends arguments as tuples so we have to unpack
    # them ourself.
    try:
        filename, limit = filename
    except ValueError:
        pass

    songname, extension = os.path.splitext(os.path.basename(filename))
    song_name = song_name or songname
    channels, Fs, file_hash = decoder.read(filename, limit)
    result = set()
    channel_amount = len(channels)

    for channeln, channel in enumerate(channels):
        # TODO: Remove prints or change them into optional logging.
        print("Fingerprinting channel %d/%d for %s" % (channeln + 1,
                                                       channel_amount,
                                                       filename))
        hashes = fingerprint.fingerprint(channel, Fs=Fs)
        print("Finished channel %d/%d for %s" % (channeln + 1, channel_amount,
                                                 filename))
        result |= set(hashes)

    return song_name, result, file_hash


def chunkify(lst, n):
    """
    Splits a list into roughly n equal parts.
    http://stackoverflow.com/questions/2130016/splitting-a-list-of-arbitrary-size-into-only-roughly-n-equal-parts
    """
    return [lst[i::n] for i in xrange(n)]
