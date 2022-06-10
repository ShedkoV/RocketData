import json
from abc import ABC, abstractmethod
import codecs
import urllib3
import requests
from bs4 import BeautifulSoup
from geopy.geocoders import Nominatim


class ParserFacade(ABC):

    def parse(self):
        page = self.get_page()
        raw_data = self.get_raw_data(page=page)
        return self.clear_data(raw_data)

    @abstractmethod
    def get_page(self):
        """Make request for getting html, xml or json data.
        It should be safe. Don't forget to wrap in try-except block."""

    @abstractmethod
    def get_raw_data(self, page: str):
        """Make dict with raw data."""

    @abstractmethod
    def clear_data(self, adverts_dict: dict):
        """Make dict with raw data."""


class Scrapper:

    def __init__(self, parser: ParserFacade, path: str):
        self.parser = parser
        self.path = path

    def process(self):    
        try:
            data = self.parser.parse()
            self.save_data(data)
            result =  {'error': False, 'data': data}
        except urllib3.exceptions.NewConnectionError as e:
            result = {'error': True, 'message': e}
        except urllib3.exceptions.MaxRetryError as e:
            result = {'error': True, 'message': e}
        except requests.exceptions.ConnectionError as e:
            result = {'error': True, 'message': e}
        except requests.exceptions.MissingSchema as e:
            result = {'error': True, 'message': e}
        except TypeError as e:
            result = {'error': True, 'message': e}
        except FileNotFoundError as e:
            result = {'error': True, 'message': e}
        return result

    def save_data(self, data):
        with codecs.open(self.path, 'w', encoding='utf-8') as file:
            json.dump(data, file, indent=2, ensure_ascii=False)


class KFCScrapper(ParserFacade):

    def __init__(self, url: str) -> None:
        self.url = url

    def get_page(self):
        return requests.get(url=self.url).json()

    def get_raw_data(self, page: str):
        return page.get('searchResults')

    def clear_data(self, kfc_dict: dict):
        return [
            {
                'address': kfc.get('storePublic', {}).get('contacts', {}).get('streetAddress', {}).get('en', 'ru'),
                'latlon': kfc.get('storePublic', {}).get('contacts', {}).get('coordinates', {}).get('geometry', {}).get('coordinates', {}),
                'name': kfc.get('storePublic', {}).get('contacts', {}).get('coordinates', {}).get('properties', {}).get('name', {}).get('en', 'ru'),
                'phones': kfc.get('storePublic', {}).get('contacts', {}).get('phoneNumber', {}),
                'working_hours': self._get_working_hours(kfc.get('storePublic', {}).get('openingHours', {}).get('regularDaily', []))
            } for kfc in kfc_dict
        ]

    def _get_working_hours(self, time_dict: dict):
        if time_dict:
            result = self._get_time_str(time_dict)
        else:
            result = ['Closed']
        return result

    def _get_time_str(self, time_dict: dict):
        days = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс']
        
        time = [
            f"{day.get('timeFrom', [])[:5]}-{day.get('timeTill', [])[:5]}"
            for day in time_dict
        ]

        days_time_map = dict(zip(time, days))

        begin = days[0]
        result = list()

        for time, end in days_time_map.items():
            result.append(f'{begin}-{end} ' + time)
            begin_index = days.index(end) + 1
            if begin_index != len(days):
                begin = days[begin_index]

        return result


class ZikoScrapper(ParserFacade):

    def __init__(self, url: str) -> None:
        self.url = url

    def get_page(self):
        return requests.get(url=self.url).json()
        
    def get_raw_data(self, page: str):
        return page

    def clear_data(self, ziko_raw_data: dict):
        return [
            {
                'address': data.get('address', {}),
                'latlon': [data.get('lat', {}), data.get('lng', {})],
                'name': data.get('title', {}),
                'phones': 'This information is not found in the API',
                'working_hours': data.get('mp_pharmacy_hours', {}).replace('<br>', ' ')
            } for _, data in ziko_raw_data.items()
        ]


class MonomahScrapper(ParserFacade):

    def __init__(self, url: str) -> None:
        self.url = url
        self.header = {
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36"
        }

    def get_page(self):
        return requests.get(url=self.url, params=self.header)
        
    def get_raw_data(self, page: str):
        soup = BeautifulSoup(page.text, 'lxml')
        return soup.find_all('div', class_='shop')

    def clear_data(self, monomah_raw_data: dict):
        return [
            {
                'address': article.find('p', 'name').text,
                'latlon': self._get_location_map(article.find('p', 'name').text, 'Минск'),
                'name': 'Мономах',
                'phones': article.find('p', 'phone').text
            } for article in monomah_raw_data
        ]

    def _get_location_map(self, shop_adress: str, city=''):
        try:
            shop_name = shop_adress[shop_adress.index('(') + 1 : shop_adress.index(')')].replace('ТРЦ', '')
            shop_name += ', ' + city  

            geolocator = Nominatim(user_agent='my_request')
            location = geolocator.geocode(shop_name)

            return [location.latitude, location.longitude]

        except AttributeError:
            return 'Not info'
            
        except ValueError:
            return 'Not info'


def result_hundler(results: list):
    for result in results:
        if result.get('error'):
            print('There is some error', result.get('message'))   


if __name__ == '__main__':

    results = list()

    kfc_scrapper = Scrapper(KFCScrapper(url='https://api.kfc.com/api/store/v2/store.get_restaurants?showClosed=true'),  path='kfs.json')
    results.append(kfc_scrapper.process())

    ziko_scrapper = Scrapper(ZikoScrapper(url='https://www.ziko.pl/wp-admin/admin-ajax.php?action=get_pharmacies'), path='ziko.json')
    results.append(ziko_scrapper.process())

    monomax_scrap =  Scrapper(MonomahScrapper(url='https://monomax.by/map'), path='monomah.json')
    results.append(monomax_scrap.process())

    result_hundler(results)
