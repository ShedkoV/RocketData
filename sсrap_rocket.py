from abc import ABC, abstractmethod
import json
import codecs
import requests

class ScrapperFacade(ABC):

    def parse(self):
        page = self.get_page()
        raw_data = self.get_raw_data(page=page)
        return self.clear_data(raw_data)

    @abstractmethod
    def get_page(self) -> str:
        """Make request for getting html, xml or json data.
        It should be safe. Don't forget to wrap in try-except block."""

    @abstractmethod
    def get_raw_data(self, page: str):
        """Make dict with raw data."""

    @abstractmethod
    def clear_data(self, adverts_dict: dict):
        """Make dict with raw data."""


class KFCScrapper(ScrapperFacade):

    def get_page(self):
        return requests.get(url='https://api.kfc.com/api/store/v2/store.get_restaurants?showClosed=true').json()
        
    def get_raw_data(self, page: str):
        return page.get('searchResults')

    def get_time_string(self, kfc_time_dict: dict) -> str:
        print(kfc_time_dict)
        return ...

    def clear_data(self, kfc_dict: dict):

        kfc_data = [
            {
                'address': kfc.get('storePublic').get('contacts').get('streetAddress').get('en', 'ru'),
                'latlon': kfc.get('storePublic').get('contacts').get('coordinates').get('geometry').get('coordinates'),
                'name': kfc.get('storePublic').get('contacts').get('coordinates').get('properties').get('name').get('en', 'ru'),
                'phones': kfc.get('storePublic').get('contacts').get('phoneNumber'),
                'working_hours': None
            } for kfc in kfc_dict
            ]

        return kfc_data


def save_data(path: str, data):
    with codecs.open(path, 'w', encoding='utf-8') as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    kfc_scrapper = KFCScrapper()
    data = kfc_scrapper.parse()
    save_data(path='kfs_restaurants.json', data=data)
