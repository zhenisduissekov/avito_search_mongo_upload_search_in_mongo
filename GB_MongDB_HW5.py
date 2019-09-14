# Good example on Youtube to do MongoDb https://www.youtube.com/watch?v=VQnmcBnguPY
#
# 1) Развернуть у себя на компьютере/виртуальной машине/хостинге MongoDB и реализовать функцию,
# записывающую собранные объявления с avito.ru в созданную БД (xpath/BS для парсинга на выбор)
# 2) Написать функцию, которая производит поиск и выводит на экран объявления с ценой меньше введенной суммы
# *Написать функцию, которая будет добавлять в вашу базу данных только новые объявления


import requests
from bs4 import BeautifulSoup
import re
import ssl
import pymongo
import json


def request_to_site(topic):
    print('Programs starts requesting from url topic: ', topic)
    url = 'https://www.avito.ru/rossiya/avtomobili?q='
    try:
        print(url+topic)
        request = requests.get(url + topic)
        if request.status_code == '200':
            print('Request was successful')
        return request.content.decode('utf-8')
    except requests.exceptions.ConnectionError:
        print('Check your internet connection!')
        exit(1)


def parse_html(topic):
    print('Program starts parsing html with topic', topic)
    html = request_to_site(topic)
    soup = BeautifulSoup(html, 'html.parser')
    parsed_text = soup.findAll('div', {'class': 'description item_table-description'})
    print('Program parsed successfully')
    return parsed_text


def input_search_word():
    input_topic = input(
        'Please enter car company and model(default: hyundai solaris):').rstrip()
    input_price: str = input('Please enter amount of money you are willing to pay for it? (default: 1.000.000) ')
    print(input_topic)
    if input_topic == '':
        input_topic: str = 'hyundai%20solaris'
    else:
        print('%20')
        input_topic = input_topic.replace(' ', '%20')
    if input_price == '':
        input_price = '1000000'
    return input_topic, input_price


def get_advertisements(parsed_text, parse_price):
    print('Program starts getting data')
    car_dict = dict()
    counter = 0
    for text in parsed_text:
        counter += 1
        car_title = text.find('a', {'class': 'item-description-title-link'})['title']
        car_title2 = text.find('span', {'itemprop': 'name'}).string
        car_url = 'https://www.avito.ru' + text.find('a', {'class': 'item-description-title-link'})['href']
        car_currency = text.find('span', {'itemprop': 'priceCurrency'})['content']
        car_price = text.find('span', {'class': re.compile(r'price.*')})['content']
        car_price2 = text.find('span', {'class': 'font_arial-rub'}).string
        car_info = text.find('div', {'class': 'specific-params specific-params_block'}).text.replace('\n', '').replace(
            '\xa0', '').replace('  ', '').split(',')
        for i in range(len(car_info)):
            car_info[i] = car_info[i].strip()
        try:
            car_info2 = text.find('div', {'class': 'js-autoteka-serp'})['data-state'].replace("\\", '')
            car_info2 = json.loads(car_info2)
            car_id = car_info2['itemId']
        except TypeError:
            car_id = car_url.split('_')[-1]
            car_info2 = 'None'

        if int(car_price) < int(parse_price):
            car_dict.setdefault(counter, {'car_id': car_id,
                                          'car_title': car_title,
                                          'car_title2': car_title2,
                                          'car_currency': car_currency,
                                          'car_price': car_price,
                                          'car_price_unit': car_price2,
                                          'car_url': car_url,
                                          'car_info': car_info,
                                          'car_info2': car_info2})
    print('Program finished getting data')
    return car_dict


def upload_to_mongo_selectively(cars_db):
    mongo_url = 'mongodb+srv://test2:test2@cluster0-bvxkt.gcp.mongodb.net/test?retryWrites=true&w=majority'
    client = pymongo.MongoClient(mongo_url, ssl=True, ssl_cert_reqs=ssl.CERT_NONE)
    db = client.get_database('avito_ru')
    records = db.avito_ads
    files_in_db_before_upload = records.count_documents({})
    print('Number of records found in DB before upload: ', files_in_db_before_upload)
    for key in cars_db:
        if not records.find_one({'car_id': cars_db[key]['car_id']}):
            records.insert_one(cars_db[key])
    files_in_db_after_upload = records.count_documents({})
    print('Number of records found in DB after upload:', files_in_db_after_upload)
    print('Upload to MongoDB finished. New files added:', files_in_db_after_upload - files_in_db_before_upload)


def input_search_word():
    input_topic = input(
        'Please enter car company and model(default: hyundai solaris):').rstrip()
    input_price: str = input('Please enter amount of money you are willing to pay for it? (default: 1.000.000) ')
    print(input_topic)
    if input_topic == '':
        input_topic: str = 'hyundai%20solaris'
    else:
        print('%20')
        input_topic = input_topic.replace(' ', '%20')
    if input_price == '':
        input_price = '1000000'
    return input_topic, input_price


def search_in_mongo_by_price(searching_price=0):
    print('Searching for cars for less than', searching_price)
    mongo_url = 'mongodb+srv://test2:test2@cluster0-bvxkt.gcp.mongodb.net/test?retryWrites=true&w=majority'
    client = pymongo.MongoClient(mongo_url, ssl=True, ssl_cert_reqs=ssl.CERT_NONE)
    db = client.get_database('avito_ru')
    records = db.avito_ads

    search_result = list(records.find({'car_price': {'$lte': searching_price}}))  # .sort({price:1})
    print('Found ', len(search_result), 'cars for less than', searching_price)
    return search_result


search_topic, search_price = input_search_word()
parsed_text_avito = parse_html(search_topic)
car_ads = get_advertisements(parsed_text_avito, search_price)
upload_to_mongo_selectively(car_ads)
# pprint.pprint(car_ads)

max_price = input('Enter your limit? (default: 500.000)')
if max_price == '':
    max_price = 500000
else:
    max_price = int(max_price)

results = search_in_mongo_by_price(max_price)
search_dict = dict()
for item in results:
    search_dict.setdefault(item['car_price'], item['car_title'])
for item in sorted(search_dict):
    print(item, search_dict[item])
