import logging

logger = logging.getLogger("ddranimtool." + __name__)


class TimeKeeper:
    def __init__(self, bpm_list=[]):
        self.bpm_list = bpm_list
        self.tick_rate = 150

    def _get_bpm_info(self, value, k1='beat_start', k2='beat_end'):
        assert (self.bpm_list is not None)

        found_bpm = None
        for test_bpm in self.bpm_list:
            if value == test_bpm[k1] and value == test_bpm[k2]:
                found_bpm = test_bpm
                break

        if found_bpm is None:
            for test_bpm in self.bpm_list:
                # BPMs with a matching start offset should take precedence
                if value >= test_bpm[k1] and value < test_bpm[k2]:
                    found_bpm = test_bpm
                    break

        if found_bpm is None:
            # But just in case none of them are within range, check the last
            # to see if it's a match (used by virt) or beyond (used by summ)
            if value >= self.bpm_list[-1][k2]:
                found_bpm = self.bpm_list[-1]

        if found_bpm is None:
            logger.error("ERROR: Couldn't find BPM!")

        assert (found_bpm is not None)
        return found_bpm

    def calculate_timestamp_from_offset(self, value):
        bpm_info = self._get_bpm_info(value, k1='beat_start', k2='beat_end')

        timestamp = bpm_info['timestamp_start']
        t = (int(value) - bpm_info['beat_start']) / 1024
        if bpm_info['bpm'] != 0:
            timestamp += (t / bpm_info['bpm']) * 60

        else:
            assert (t == 0)

        return timestamp * 1000

    def calculate_offset_from_timestamp(self, value):
        value = (value / 1000) * self.tick_rate
        bpm_info = self._get_bpm_info(value, k1='music_start', k2='music_end')

        offset = bpm_info['beat_start'] + (bpm_info['beat_end'] - bpm_info['beat_start']) * (
            (value - bpm_info['music_start']) / (bpm_info['music_end'] - bpm_info['music_start']))

        return int(offset)

    def get_bpm_from_offset(self, value):
        return self._get_bpm_info(value, k1='beat_start', k2='beat_end')['bpm']

    def get_bpm_from_timestamp(self, value):
        value = (value / 1000) * self.tick_rate
        return self._get_bpm_info(value, k1='music_start', k2='music_end')['bpm']
