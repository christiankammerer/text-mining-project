import requests as req # http requests
from lxml import etree # xml parsing
from typing import Tuple

class Party:
    def __init__(self, name, abbreviation):
        self.name = name
        self.abbreviation = abbreviation
        self.speakers = []

    def add_speaker(self, speaker):
        self.speakers.append(speaker)

    def __str__(self):
        return f"{self.name} ({self.abbreviation})"
    
    def __repr__(self):
        return f"Party(name={self.name}, abbreviation={self.abbreviation}) speakers={self.speakers}"

class Speaker:
    def __init__(self, id, first_name, last_name, party):
        self.id = id
        self.first_name = first_name
        self.last_name = last_name
        self.party = party
        self.speeches = []
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.party})"
    
    def __repr__(self):
        return f"Speaker(id={self.id}, first_name={self.first_name}, last_name={self.last_name}, party={self.party})"
    
class Session:
    def __init__(self, data):
        self.id = data.get("id")
        self.date = data.get("date")
        self.number = data.get("number")
        self.protocol_id = data.get("protocolId")
        self.speeches = []

class Speech:
    def __init__(self, data):
        self.id = data.get("id")
        self.speaker_id = data.get("speakerId")
        self.session_id = data.get("sessionId")
        self.text = data.get("text")

class Protocol:
    def __init__(self, data):
        self.id = data.get("id")
        self.datum = data.get("datum")
        self.wahlperiode = data.get("wahlperiode")
        self.vorgangstyp = data.get("vorgangstyp")
        self.herausgeber = data.get("herausgeber")
        self.xml_link = data.get("fundstelle").get("xml_url")
        self.xml_content = self.fetch_xml()
        
    def fetch_xml(self):
        response = req.get(self.xml_link)
        return response.text
    
    def parse_xml(self):
        root = etree.fromstring(self.xml_content.encode('utf-8'))
        speeches_raw = root.findall('.//rede')
        speakers = []
        speeches = []

        for speech in speeches_raw:
            speaker, speech = self.parse_speech(speech)
            speakers.append(speaker)
            speeches.append(speech)
        return speakers, speeches

    def parse_speech(self, speech_element: etree._Element) -> Tuple[Speaker, Speech]:
        speaker_element = speech_element.find('.//redner')
        name = speaker_element.find("name")
        text_element = speech_element.find('.//text')

        # Ministers and other officials do not have a party affiliation in the XML, 
        # this needs to be handled through a lookup table
        speaker = Speaker(
            id =  speaker_element.get("id"),
            first_name = name.find("vorname").text,
            last_name = name.find("nachname").text,
            party = name.find("fraktion").text if name.find("fraktion") is not None else ""
        )

        speech = Speech({
            "id": speech_element.get("id"),
            "speakerId": speaker.id,
            "sessionId": self.id,
            "text": text_element.text if text_element is not None else ""
        })
        return speaker, speech

class DataFetcher:
    def __init__(self, api_key: str, start_date: str = None, end_date: str = None, 
                 entity: str = None, resource_type: str = None):
        
        self.api_key = api_key
        self.start_date = start_date
        self.end_date = end_date
        self.entity = entity
        self.resource_type = resource_type

    def fetch_list_of_protocols(self) -> list:
        """
        Fetches a list of full-text protocols from the Bundestag API based on the parameters of the DataFetcher instance.
        
        Returns:
            list: A list of meta data of protocol documents (dicts) retrieved from the API.
        """
        
        # Build query parameters dynamically
        params = {
            'apikey': self.api_key,
            'f.datum.start': self.start_date,
            'f.datum.end': self.end_date,
            'f.zuordnung': self.entity

        }
        
        # Filter out None values
        params = {k: v for k, v in params.items() if v is not None}
        
        url_string = f"https://search.dip.bundestag.de/api/v1/{self.resource_type}"

        responses = []
        response = req.get(url_string, params=params).json()
        responses.append(response)

        # Bundestag API provides a maximum of 100 documents per request, pagination is done through cursor
        # Call with the same parameters + cursos will return the next 100 documents
        while len(response.get("documents", [])) == 100:
            cursor = response.get("cursor")
            params['cursor'] = cursor
            response = req.get(url_string, params=params).json()
            responses.append(response)

        documents = [doc for resp in responses for doc in resp.get("documents", [])] # Flatten list of documents
        return documents
    
    def fetch_protocol_by_id(self, protocol_id: str) -> dict:
        """
        Fetches a single protocol by its ID from the Bundestag API.

        Args:
            protocol_id (str): The ID of the protocol to fetch. 
        Returns:
            dict: The protocol data as a dictionary.
        """
        url_string = f"https://search.dip.bundestag.de/api/v1/{self.resource_type}"
        params = {
            'apikey': self.api_key,
            'f.id' : protocol_id
        }
        response = req.get(url_string, params=params).json()
        return response
    
parties = [
    Party(name = "Christlich Demokratische / Soziale Union Deutschlands", abbreviation = "CDU / CSU"),
    Party(name = "Sozialdemokratische Partei Deutschlands", abbreviation = "SPD"),
    Party(name = "Bündnis 90/Die Grünen", abbreviation = "GRÜNE"),
    Party(name = "Freie Demokratische Partei", abbreviation = "FDP"),
    Party(name = "Die Linke", abbreviation = "DIE LINKE"),
    Party(name = "Alternative für Deutschland", abbreviation = "AfD"),
    Party(name = "Fraktionslos", abbreviation = "fraktionslos"),
]