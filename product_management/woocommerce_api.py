import base64
import json
import requests
import logging  # Import the logger module
import os
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from requests_toolbelt.multipart.encoder import MultipartEncoder
import uuid
#import uuid


# Define the logger object
logger = logging.getLogger(__name__)

class WooCommerceAPI:
    def __init__(self):
        self.url = settings.WOOCOMMERCE_URL
        self.consumer_key = settings.WOOCOMMERCE_CONSUMER_KEY
        self.consumer_secret = settings.WOOCOMMERCE_CONSUMER_SECRET
        self.wp_url = settings.WORDPRESS_API_URL
        self.wc_url = settings.WOOCOMMERCE_API_URL
        self.wp_auth = (settings.WORDPRESS_USERNAME, settings.WORDPRESS_APP_PASSWORD)

    def get_product(self, product_id):
        response = requests.get(
            f"{self.url}/products/{product_id}",
            auth=(self.consumer_key, self.consumer_secret)
        )
        return response.json()
    def update_product(self, product_id, data):
        response = requests.put(
            f"{self.url}/products/{product_id}",
            json=data,
            auth=(self.consumer_key, self.consumer_secret)
        )
        return response.json()

    def get_products(self, page=1, per_page=10, category=None, search=None):
        params = {
            'page': page,
            'per_page': per_page,
        }
        if category:
            params['category'] = category
        if search:
            params['search'] = search

        response = requests.get(
            f"{self.url}/products",
            auth=(self.consumer_key, self.consumer_secret),
            params=params
        )
        return response.json(), response.headers

    def get_categories(self):
        response = requests.get(
            f"{self.url}/products/categories",
            auth=(self.consumer_key, self.consumer_secret),
            params={'per_page': 100}  # Ajusta este número según tus necesidades
        )
        return response.json()

    
    
    def upload_image(self, image_file):
    # Generar un nombre único para el archivo
        file_name, file_extension = os.path.splitext(image_file.name)
        unique_filename = f"{file_name}_{uuid.uuid4().hex}{file_extension}"
        
        # Crear un MultipartEncoder para manejar la carga del archivo
        m = MultipartEncoder(
            fields={
                'file': (unique_filename, image_file, image_file.content_type),
                'title': unique_filename,
            }
        )
        
        headers = {
            'Content-Type': m.content_type
        }
        
        response = requests.post(
            f"{self.wp_url}/media",
            data=m,
            headers=headers,
            auth=self.wp_auth
        )
        
        print(f"Respuesta de la API: Status {response.status_code}")
        print(f"Respuesta de la API: {response.text}")
        
        try:
            json_response = response.json()
            if 'id' in json_response:
                return {
                    'id': json_response['id'],
                    'source_url': json_response['source_url']
                }
            else:
                return {
                    'id': None,
                    'source_url': None,
                    'error': json_response.get('message', 'Unknown error')
                }
        except json.JSONDecodeError:
            return {
                'id': None,
                'source_url': None,
                'error': 'Invalid JSON response from server'
            }







    def create_product(self, data):
        response = requests.post(
            f"{self.wc_url}/products",
            json=data,
            auth=(self.consumer_key, self.consumer_secret)
        )
        return response.json()




