import pandas as pd
import overpy
from geopy.geocoders import Nominatim
from geopy.extra.rate_limiter import RateLimiter
from datetime import datetime, timedelta
import os

api_url = "http://overpass-api.de/api/interpreter"
api = overpy.Overpass()
geolocator = Nominatim(user_agent="osm_processor")
geocode = RateLimiter(geolocator.reverse, min_delay_seconds=1)

def get_province_district(lat, lon):
    try:
        location = geolocator.reverse((lat, lon), exactly_one=True)
        address = location.raw.get('address', {})
        province = address.get('region', '')
        district = address.get('suburb', '')
        return province, district
    except Exception as e:
        print(f"Error en la geocodificación: {e}")
        return "", ""

def fetch_historical_data(start_date, end_date, amenities):
    date_range = pd.date_range(start=start_date, end=end_date, freq='W')
    data = []

    for date in date_range:
        print(f"Consultando datos para la fecha: {date}")
        query = f"""
        [date:"{date.strftime('%Y-%m-%dT00:00:00Z')}"];
        area[name="Lima"]->.searchAreaLima;
        area[name="Callao"]->.searchAreaCallao;
        (
          node["amenity"~"^({'|'.join(amenities)})$"](area.searchAreaLima);
          node["amenity"~"^({'|'.join(amenities)})$"](area.searchAreaCallao);
          way["amenity"~"^({'|'.join(amenities)})$"](area.searchAreaLima);
          way["amenity"~"^({'|'.join(amenities)})$"](area.searchAreaCallao);
          relation["amenity"~"^({'|'.join(amenities)})$"](area.searchAreaLima);
          relation["amenity"~"^({'|'.join(amenities)})$"](area.searchAreaCallao);
        );
        out body;
        >;
        out skel qt;
        """
        try:
            result = api.query(query)
            if result.nodes:
                print('Hubo resultados:',len(result.nodes))
            else:
                print('No hubo resultados.')
            
            for node in result.nodes:
                province, district = get_province_district(node.lat, node.lon)
                data.append({
                    "id": node.id,
                    "fecha": date.strftime('%d/%m/%Y'),
                    "province": province,
                    "district": district,
                    "lat": node.lat,
                    "lon": node.lon,
                    "amenity": node.tags.get("amenity")
                })
        except Exception as e:
            print(f"Error al ejecutar la consulta para la fecha {date}: ", e)

    return pd.DataFrame(data)

amenities = [
    "sanitary_dump_station", "recycling", "waste_basket",
    "waste_disposal", "waste_transfer_station"
]

# Cambiar según fecha

for i in range(0,5):
    start = f'202{i}-01-01'
    end = f'202{i}-05-01'

    df = fetch_historical_data(start, end, amenities)
    if not df.empty:
        df.to_csv("amenities_lima_callao_historical.csv", index=False,mode='a',header=not os.path.exists("amenities_lima_callao_historical.csv"))
        print("Datos guardados en amenities_lima_callao_historical.csv")
    else:
        print("No se encontraron datos en el intervalo de tiempo especificado.")
