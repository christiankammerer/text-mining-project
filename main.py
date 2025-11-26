from config import parties

from helper import DataFetcher, Protocol

api_key = "OSOegLs.PR2lwJ1dwCeje9vTj7FPOt3hvpYKtwKkhw"
start_date = "2022-01-01"
end_date = "2023-01-01"
entity = "BT"
resource_type = "plenarprotokoll"
data_fetcher = DataFetcher(api_key=api_key, start_date=start_date, end_date=end_date, 
                           entity=entity, resource_type=resource_type)

data = data_fetcher.fetch_list_of_protocols()

protocols = [Protocol(protocol_data) for protocol_data in data]


