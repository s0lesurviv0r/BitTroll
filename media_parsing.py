from ffprobe import FFProbe

class Metadata:
    """Object represents metadata for a media file"""
    def __init__(self):
        self.tags = {}

    def exists(self,tag):
        if tag in self.tags:
            return True

        return False

    def add(self,tag,value):
        if self.exists(tag) is False:
            self.tags[tag] = value

    def get(self,tag):
        if tag in self.tags:
            return self.tags[tag]

        return False

    def empty(self):
        if self.tags:
            return False

        return True

    def get_json(self):
        return self.tags

@staticmethod
def get_media_params(file_path):
    m = Metadata()

    try:
        metadata = FFProbe(file_path)

        if metadata.html5SourceType() != "":
            m.add("html5_source_type", metadata.html5SourceType())

        if metadata.bitrate() != 0.0:
            m.add("bit_rate", metadata.bitrate())

        if metadata.durationSeconds() != 0.0:
            m.add("duration", metadata.durationSeconds())

        for stream in metadata.streams:
            if stream.isVideo():
                (width,height) = stream.frameSize()
                if int(width) != 0 and int(height) != 0:
                    m.add("width",width)
                    m.add("height",height)

                if int(stream.frames()) != 0:
                    m.add("frames",stream.frames())
    except Exception as e:
        pass

    """Fallback and calculate bit rate or duration if missing using available data"""
    if m.exists("bit_rate") and m.exists("duration") is False:
        size = os.path.getsize(full_path)
        m.add("duration", (m.get("bit_rate")/8) * size)

    if m.exists("duration") and m.exists("bit_rate") is False:
        size = os.path.getsize(full_path)
        m.add("bit_rate", (size / m.get("duration"))*8)

    if m.exists("frames") and m.exists("duration") and m.exists("frame_rate") is False:
        m.add("frame_rate", int(m.get("frames")/m.get("duration")))

    """If we have some values then return them if not then return False"""
    if m.empty() is False:
        return m

    return False
