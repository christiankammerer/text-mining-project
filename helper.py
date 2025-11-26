import requests as req # http requests
from lxml import etree # xml parsing
from typing import Tuple

class Party:
    def __init__(self, name: str, abbreviation: str):
        self.name = name
        self.abbreviation = abbreviation
        self.speakers: list['Speaker'] = []

    def add_speaker(self, speaker: 'Speaker') -> None:
        self.speakers.append(speaker)

    def __str__(self):
        return f"{self.name} ({self.abbreviation})"
    
    def __repr__(self):
        return f"Party(name={self.name}, abbreviation={self.abbreviation}) speakers={self.speakers}"

class Speaker:
    def __init__(self, id: str, first_name: str, last_name: str, party: str):
        self.id = id
        self.first_name = first_name
        self.last_name = last_name
        self.party = party
        self.speeches: list['Speech'] = []
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.party})"
    
    def __repr__(self):
        return f"Speaker(id={self.id}, first_name={self.first_name}, last_name={self.last_name}, party={self.party})"
    
    def __eq__(self, other):
        return isinstance(other, Speaker) and self.id == other.id
    
    def __hash__(self):
        return hash(self.id)
    
class Session:
    def __init__(self, id: str, date: str, wahlperiode: str, sitzungsnr: str, protocol_id: str):
        self.id = id
        self.wahlperiode = wahlperiode
        self.sitzungsnr = sitzungsnr
        self.date = date
        self.protocol_id = protocol_id
        self.speeches: list['Speech'] = []
        self.speakers: list['Speaker'] = []

class Speech:
    def __init__(self, id: str, speaker_id: str, session_id: str, text: str):
        self.id = id
        self.speaker_id = speaker_id
        self.session_id = session_id
        self.text = text

    def split_into_parts(self, max_length: int) -> list[str]:
        words = self.text.split()
        parts = []
        current_part = []

        for word in words:
            # Check if adding the next word would exceed the max length
            if len(' '.join(current_part + [word])) <= max_length:
                current_part.append(word)
            else:
                # If it would exceed, save the current part and start a new one
                parts.append(' '.join(current_part))
                current_part = [word]

        # Add any remaining words as the last part
        if current_part:
            parts.append(' '.join(current_part))

        return parts

class Protocol:
    def __init__(self, data: dict):
        self.id = data.get("id")
        self.datum = data.get("datum")
        self.wahlperiode = data.get("wahlperiode")
        self.vorgangstyp = data.get("vorgangstyp")
        self.herausgeber = data.get("herausgeber")
        fundstelle = data.get("fundstelle")
        if fundstelle:
            self.xml_link = fundstelle.get("xml_url")
        else:
            raise ValueError("No fundstelle found in protocol data, cannot fetch XML")
        self.xml_content = self.fetch_xml()
        self.session_nr: str = ""
        
    def fetch_xml(self) -> str:
        """
        Fetches the XML content from the provided xml_link.
        Returns:
            str: The XML content as a string.
        """
        response = req.get(self.xml_link)
        return response.text
    
    def parse_xml(self) -> Tuple[list[Speaker], list[Speech]]:
        root = etree.fromstring(self.xml_content.encode('utf-8'))
        sitzungsnr_element = root.find('.//sitzungsnr')
        if sitzungsnr_element is not None:
            self.session_nr = sitzungsnr_element.text or ""
        else:
            self.session_nr = ""
        speeches_raw = root.findall('.//rede')
        speakers_set = set()
        speeches = []

        for speech in speeches_raw:
            speaker, speech = self.parse_speech(speech)
            speakers_set.add(speaker)
            speeches.append(speech)
        return list(speakers_set), speeches

    def parse_speech(self, speech_element: etree._Element) -> Tuple[Speaker, Speech]:
        speaker_element = speech_element.find('.//redner')
        if speaker_element is None:
            raise ValueError("No speaker element found in speech")
            
        name = speaker_element.find("name")
        if name is None:
            raise ValueError("No name element found in speaker")

        # Ministers and other officials do not have a party affiliation in the XML, 
        # this needs to be handled through a lookup table
        vorname = name.find("vorname")
        nachname = name.find("nachname")
        fraktion = name.find("fraktion")
        
        first_name = vorname.text if vorname is not None and vorname.text else ""
        last_name = nachname.text if nachname is not None and nachname.text else ""
        party = fraktion.text if fraktion is not None and fraktion.text else ""
            
        speaker = Speaker(
            id = speaker_element.get("id") or "",
            first_name = first_name, 
            last_name = last_name,
            party = party
        )

        # Extract all text content from the speech, including nested elements
        # Use itertext() to get all text nodes, or join all <p> elements
        speech_text_parts = []
        for p_element in speech_element.findall('.//p'):
            if p_element.text:
                speech_text_parts.append(p_element.text.strip())
        
        speech_text = " ".join(speech_text_parts) if speech_text_parts else ""
        
        speech = Speech(
            id=speech_element.get("id") or "",
            speaker_id=speaker.id,
            session_id=self.id or "",
            text=speech_text
        )
        return speaker, speech
    
    def to_session(self) -> Session:
        session = Session(
            id=self.id or "",
            date=self.datum or "",
            wahlperiode=self.wahlperiode or "",
            sitzungsnr=self.session_nr,  
            protocol_id=self.id or ""
        )
        speakers, speeches = self.parse_xml()
        session.speeches = speeches
        session.speakers = speakers
        return session

class DataFetcher:
    def __init__(self, api_key: str, start_date: str = "2024-01-01", end_date: str = "2024-12-31", 
                 entity: str = "BT", resource_type: str = "plenarprotokoll"):
        
        self.api_key = api_key
        self.start_date = start_date
        self.end_date = end_date
        self.entity = entity
        self.resource_type = resource_type

    def fetch_list_of_protocols(self) -> list[dict]:
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
            'f.id' : protocol_id,
            'f.zuordnung' : self.entity
        }
        response = req.get(url_string, params=params).json()
        return response