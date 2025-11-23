class Party:
    def __init__(self, data):
        self.id = data.get("id")
        self.name = data.get("name")
        self.abbreviation = data.get("abbreviation")
        self.speakers = []

    def add_speaker(self, speaker):
        self.speakers.append(speaker)

class Speaker:
    def __init__(self, data):
        self.id = data.get("id")
        self.first_name = data.get("firstName")
        self.last_name = data.get("lastName")
        self.party_id = data.get("partyId")
        self.speeches = []

class Speech:
    def __init__(self, data):
        self.id = data.get("id")
        self.speaker_id = data.get("speakerId")
        self.session_id = data.get("sessionId")
        self.text = data.get("text")
    
class Session:
    def __init__(self, data):
        self.id = data.get("id")
        self.date = data.get("date")
        self.number = data.get("number")
        self.protocol_id = data.get("protocolId")
        self.speeches = []
