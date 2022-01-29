from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from time import sleep
import csv
import ssl
from bson import ObjectId
import pymongo

chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument('disable-infobars')
chrome_options.add_argument('--disable-notifications')
chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
chrome_options.add_experimental_option('useAutomationExtension', False)
chrome_options.add_argument('--disable-popup-blocking')
driver = webdriver.Chrome(
    executable_path='/Users/hadarisraeli1/Desktop/Hadar/icsScraper/chromedriver',
    options=chrome_options)
driver.maximize_window()

DIGIKEY_URL = 'https://www.digikey.com/'
TOP_RESULT_PATH = '//*[@class="MuiTableCell-root MuiTableCell-body jss123"]//a'
ITEMS_QUANTITY_PATH = '//*[@class="MuiTableCell-root MuiTableCell-body jss123"][1]//span//span'
TEXTBOX_PATH = '//*[@class="header__searchinput dkdirchanger product-search-text search-textbox"]'
SEARCH_BUTTON_PATCH = '//*[@class="header__search"]//button'
TIME_TO_WAIT = 60

MONGO_DETAILS = \
    "mongodb+srv://ics-Scraper:ginger2016@cluster0.2woo5.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
client = pymongo.MongoClient(MONGO_DETAILS, ssl_cert_reqs=ssl.CERT_NONE)
database = client.ics_scraper
manufacturers_collection = database.get_collection('manufacturers')
products_collection = database.get_collection('products')


def open_website():
    driver.get(DIGIKEY_URL)
    WebDriverWait(driver, TIME_TO_WAIT).until(EC.presence_of_element_located((By.XPATH, TEXTBOX_PATH)))


def search_manufacturer_url(manufacturer: str):

    if driver.find_elements_by_xpath(TEXTBOX_PATH):
        search = driver.find_element_by_xpath(TEXTBOX_PATH)
        search.clear()
        search.send_keys(manufacturer)
    else:
        print("No Search Field Found")

    if driver.find_elements_by_xpath(SEARCH_BUTTON_PATCH):
        search_btn = driver.find_element_by_xpath(SEARCH_BUTTON_PATCH)
        search_btn.click()
    else:
        print("No Search Button Found")


def extract_num_from_str(item: str)-> int:
    num_in_str = item.text
    if "(" in num_in_str:
        num_in_str = num_in_str.replace("(", "")
    else:
        num_in_str = num_in_str
    if ")" in num_in_str:
        num_in_str = num_in_str.replace(")", "")
    else:
        num_in_str = num_in_str
    if " " in num_in_str:
        num_in_str = num_in_str.split(" ")[0]
    if "," in num_in_str:
        num_in_str = num_in_str.replace(",", "")
    else:
        num_in_str = num_in_str
    return int(num_in_str)


def check_product_exist(manufacturer_products: str, product_name: str) -> bool:
    for product in manufacturer_products:
        if product_name == product['name']:
            return True
    return False


def extract_url(manufacturer: str):
    search_manufacturer_url(manufacturer)
    top_results = driver.find_elements_by_xpath(TOP_RESULT_PATH)
    items = driver.find_elements_by_xpath(ITEMS_QUANTITY_PATH)
    len_of_top_res = len(top_results)
    new_products_to_insert = []
    product_details = dict()
    manufacturer_products = products_collection.find({"manufacturer": manufacturer})
    for i in range(len_of_top_res):
        url = top_results[i]
        count = items[i]
        product_details['manufacturer'] = manufacturer
        product_details['name'] = url.text
        product_details['url'] = url.get_attribute('href')
        product_details['num_of_products'] = extract_num_from_str(count)
        if not check_product_exist(manufacturer_products, product_details['name']):
            new_products_to_insert.append(product_details.copy())

    for product in new_products_to_insert:
        products_collection.insert_one(product)


def extract_urls():
    open_website()
    try:
        for manufacturer_data in manufacturers_collection.find():
            manufacturer = manufacturer_data['manufacturer']
            extract_url(manufacturer)

    except Exception as ex:
        print(ex)

    finally:
        driver.close()


def add_new_manufacturer(new_manufacturer: str):
    manufacturer = manufacturers_collection.find_one({"manufacturer": new_manufacturer})
    if not manufacturer:
        manufacturers_collection.insert_one({'manufacturer': new_manufacturer})
    else:
        print("Manufacturer exists")


def delete_manufacturer(manufacturer: str):
    manufacturer = manufacturers_collection.find_one({"manufacturer": manufacturer})
    if manufacturer:
        manufacturers_collection.delete_one({"manufacturer": manufacturer})


def find_manufacturer_top_products(manufacturer: str):
    open_website()
    extract_url(manufacturer)
    driver.close()


def find_manufacturers_top_products():
    extract_urls()


