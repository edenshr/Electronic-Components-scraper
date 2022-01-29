import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
import re
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import Select
import time
import pandas as pd
import pprint
import os
import sys
from datetime import datetime
from lxml import html
from urllib.parse import urljoin
import sqlite3
import csv
import glob
import numpy as np
import pymongo
import ssl


INPUT_BROWSER_PATH = '/Users/hadarisraeli1/Desktop/Hadar/icsScraper/chromedriver'
#INPUT_BROWSER_PATH = "/Users/edenshrian/Desktop/Documents/Eden Shrian/Eden/Chrome Driver/chromedriver"

MONGO_DETAILS = \
    "mongodb+srv://ics-Scraper:ginger2016@cluster0.2woo5.mongodb.net/myFirstDatabase?retryWrites=true&w=majority"
client = pymongo.MongoClient(MONGO_DETAILS, ssl_cert_reqs=ssl.CERT_NONE)
database = client.ics_scraper
# manufacturers_collection = database.get_collection('manufacturers')
products_collection = database.get_collection('products')
digikey_data_collection = database.get_collection(('digikey_data'))


class DigikeyScraper:

    PAGE_LOAD_TIMEOUTS = 120.0

    def __init__(self, input_browser_path, input_start_url):
        self.TIME_PAUSE = 1.0
        self.is_interrupted = False
        self.inputs_are_good = True

        if type(input_browser_path) != str:
            print("Browser path must be a string!")
            self.inputs_are_good = False
        if type(input_start_url) != str:
            print("Start URL must be a string!")
            self.inputs_are_good = False
        if not self.inputs_are_good:
            print("Some input is of wrong type!")
            return

        self.PATH_TO_BROWSER = input_browser_path
        self.start_url = input_start_url
        self.driver = self.start_driver_normal()
        return

    def scrape_and_write_data(self):
        if self.is_interrupted:
            return

        print("Scraping data...")
        pagination_scraped = False
        data_to_write = dict()
        current_page = 1
        last_good_scraped_url = ""
        consecutive_fails = 0
        page_started_scraping_at = time.time()
        past_iter_ids = list()
        headers = list()

        while time.time() - page_started_scraping_at < DigikeyScraper.PAGE_LOAD_TIMEOUTS:
            current_iter_ids = list()
            is_rerunning_page = False
            if current_page == 1 or consecutive_fails >= 5:

                try:
                    self.destroy_handles_and_create_new_one()
                    if current_page == 1:
                        self.driver.get(self.start_url)
                    else:
                        print("Too many wait fails, try again at URL", last_good_scraped_url)
                        is_rerunning_page = True
                        self.driver.get(last_good_scraped_url)
                        past_iter_ids = []
                    wait_for_products = self.wait_by_xpath(
                        "//table[@class='MuiTable-root' and contains(@id, 'data-table')]/tbody/tr", 30)
                except KeyboardInterrupt:
                    print("Manual interrupt, quit!")
                    self.is_interrupted = True
                    self.driver.quit()
                    return
                # TODO: Fix exceptions
                except:
                    print("An exception at", self.start_url)
                    continue
            else:
                pass

            try:
                inner_html = self.driver.execute_script("return document.body.innerHTML")
                html_elem = html.document_fromstring(inner_html)
                current_page_products = self.parse_out_products(html_elem)
                current_iter_ids = sorted([current_page_product["Product_ID"] for current_page_product in current_page_products])
                if len(current_iter_ids) != 0 and current_iter_ids != past_iter_ids:

                    for product_to_add in current_page_products:
                        data_to_write[product_to_add["Product_ID"]] = product_to_add

                    past_iter_ids = [current_iter_id for current_iter_id in current_iter_ids]

                    if not headers:
                        headers = [head_item for head_item in current_page_products[0]]

                    last_good_scraped_url = self.driver.current_url
                    consecutive_fails = 0
                else:
                    time.sleep(2.0)
                    consecutive_fails += 1
                    continue

            except KeyboardInterrupt:
                print("Manual interrupt, quit!")
                self.is_interrupted = True
                self.driver.quit()
                return

            # TODO: Fix exceptions
            except:
                print("An exception at", self.start_url)
                continue

            if is_rerunning_page:
                current_page -= 1
            print("Scraped page", current_page)
            next_page_el = html_elem.xpath("//div[@data-testid='pagination-container']/button[@title='Next Page']")
            if len(next_page_el) == 0:
                pagination_scraped = True
                break
            else:

                for click_try in range(0, 10):
                    try:
                        self.driver.execute_script(
                            "arguments[0].click();",
                            self.driver.find_elements_by_xpath(
                                "//div[@data-testid='pagination-container']/button[@title='Next Page']"
                            )[0])
                        time.sleep(2.0)
                        break

                    except KeyboardInterrupt:
                        print("Manual interrupt, quit!")
                        self.is_interrupted = True
                        self.driver.quit()
                        return
                    except:
                        print("An exception while trying to click on next page button!")
                        time.sleep(2.0)
                        continue

                current_page += 1
                page_started_scraping_at = time.time()

        if not pagination_scraped:
            print("Couldn't scrape from", self.start_url)
            self.driver.quit()
            return

        for row in data_to_write.values():
            digikey_data_collection.insert_one(self.row_to_write_helper(row))

        # outfile_name = datetime.now().strftime("%d-%m-%Y %H_%M_%S") + " digikey.csv"
        # outfile = open(outfile_name, 'w', newline='', encoding='utf-8')
        # writer = csv.writer(outfile, delimiter=",", quoting=csv.QUOTE_MINIMAL)
        # ccc = writer.writerow(HEADERS)
        #
        # for product_to_write in data_to_write:
        #     row_to_write = []
        #     for header_item in HEADERS:
        #         if header_item in data_to_write[product_to_write]:
        #             row_to_write.append(data_to_write[product_to_write][header_item])
        #         else:
        #             row_to_write.append("")
        #
        #     ccc = writer.writerow(row_to_write)
        #
        # outfile.close()
        # print("Created output file:", outfile_name)

        self.driver.quit()
        return

    def parse_out_products(self, input_tree):

        products_to_return = []
        headers = [self.fix_string(header_el.text_content()) for header_el in input_tree.xpath("//table[@class='MuiTable-root' and contains(@id, 'data-table')]/thead/tr[1]/th")]

        product_els = input_tree.xpath("//table[@class='MuiTable-root' and contains(@id, 'data-table')]/tbody/tr")
        for product_el in product_els:
            row_data_els = product_el.xpath("./td")
            if len(headers) == 0 or len(headers) != len(row_data_els):
                continue


            this_product = {}
            for header_index, header_text in enumerate(headers):

                multirow_els = row_data_els[header_index].xpath("./span[not(@class)]/div")
                if len(multirow_els) == 0:
                    data_value = self.fix_string(row_data_els[header_index].text_content())
                    this_product[header_text] = data_value
                else:
                    this_product[header_text] = "\n".join([self.fix_string(multirow_el.text_content()) for multirow_el in multirow_els])

                current_data_attrib = None
                try:
                    current_data_attrib = row_data_els[header_index].attrib["data-atag"]
                except KeyError:
                    pass

                if current_data_attrib == 'tr-supplier':
                    this_product["Supplier_URL"] = ''
                    supplier_el = row_data_els[header_index].xpath("./a[@href]")
                    if len(supplier_el) != 0:
                        this_product["Supplier_URL"] = urljoin('https://www.digikey.com/', supplier_el[0].attrib["href"])
                elif current_data_attrib == 'tr-product':
                    this_product["Product_ID"] = ''
                    this_product["Product_Model"] = ''
                    this_product["Product_Name"] = ''
                    this_product["Product_URL"] = ''
                    this_product["Product_Specs_URL"] = ''
                    this_product["Product_Image_URL"] = ''

                    prodid_el = row_data_els[header_index].xpath(".//a[@data-product-id and @href]")
                    if len(prodid_el) != 0:
                        this_product["Product_ID"] = prodid_el[0].attrib["data-product-id"]
                        this_product["Product_Model"] = self.fix_string(prodid_el[0].text_content())
                        this_product["Product_URL"] = urljoin('https://www.digikey.com/', prodid_el[0].attrib["href"])

                    prodname_el = row_data_els[header_index].xpath(".//div[contains(@data-testid, 'product-description')]")
                    if len(prodname_el) != 0:
                        this_product["Product_Name"] = self.fix_string(prodname_el[0].text_content())

                    prodspecs_el = row_data_els[header_index].xpath(".//div[contains(@track-data, 'asset_type=Datasheet')]/a[@href]")
                    if len(prodspecs_el) != 0:
                        prodspecs_url = prodspecs_el[0].attrib["href"]
                        prodspecs_url = urljoin('https://', prodspecs_url)
                        this_product["Product_Specs_URL"] = prodspecs_url

                    prodimage_el = row_data_els[header_index].xpath(".//img[@src and contains(@data-testid, 'product-image')]")
                    if len(prodimage_el) != 0:
                        prodimage_url = prodimage_el[0].attrib["src"]
                        prodimage_url = urljoin('https://', prodimage_url)
                        this_product["Product_Image_URL"] = prodimage_url

                else:
                    pass

            products_to_return.append(this_product)

        return products_to_return

    def wait_by_xpath(self, xp, how_long_to_wait):
        try:
            WebDriverWait(self.driver, how_long_to_wait).until(EC.presence_of_element_located((By.XPATH, xp)) )
            time.sleep(self.TIME_PAUSE)
            return 1
        except TimeoutException:
            print ("Too much time has passed while waiting for", xp)
            return 0

    def fix_string(self, entry_string):
        exit_string = entry_string.replace("\n", "")
        exit_string = exit_string.replace("\t", "")
        exit_string = exit_string.replace("\r", "")
        while "  " in exit_string:
            exit_string = exit_string.replace("  ", " ")
        if len(exit_string) > 0:
            if exit_string[0] == ' ':
                exit_string = exit_string[1:len(exit_string)]
        if len(exit_string) > 0:
            if exit_string[len(exit_string)-1] == ' ':
                exit_string = exit_string[0:len(exit_string)-1]

        return exit_string

    def price_fixer(self, price:str):
        try:
           price = float(price)
        except:
            price = price
        finally:
            return price

    def row_to_write_helper(self, row: dict) -> dict:
        return {
            "Mfr Part #": row['Mfr Part #'],
            'Product_Model': row['Product_Model'],
            'Product_Name': row['Product_Name'],
            'Price': self.price_fixer(row['Price']),
            'Part Status': row['Part Status'],
            'Supplier': row['Supplier']
        }

    def start_driver_normal(self):
        normal_driver = webdriver.Chrome(self.PATH_TO_BROWSER)
        normal_driver.maximize_window()
        return normal_driver

    def start_driver_headless(self):
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("window-size=1920,1080")
        headless_driver = webdriver.Chrome(self.PATH_TO_BROWSER, options=chrome_options)
        return headless_driver

    def destroy_handles_and_create_new_one(self):

        while 1:
            initial_handles = self.driver.window_handles
            self.driver.execute_script("window.open();")
            handles_after_opening = self.driver.window_handles
            if len(handles_after_opening) > len(initial_handles):
                break
            else:
                print("Couldn't open a handle!")
                time.sleep(10.0)
                continue

        added_handle = []
        for handle in handles_after_opening:
            if handle in initial_handles:
                self.driver.switch_to.window(handle)
                self.driver.close()
            else:
                added_handle.append(handle)

        self.driver.switch_to.window(added_handle[0])
        return


def get_url_by_mfg(manufacturer:str) -> dict:
    manufacturer_data = products_collection.find({"manufacturer": manufacturer})
    return [row['url'] for row in manufacturer_data]


def write_data_by_mfg(manufacturer: str):
    urls = get_url_by_mfg(manufacturer)
    for url in urls:
        scraper = DigikeyScraper(INPUT_BROWSER_PATH, url)
        scraper.scrape_and_write_data()


def write_all_data():
    manufacturers = products_collection.find()
    for manufacturer in manufacturers:
        scraper = DigikeyScraper(INPUT_BROWSER_PATH, manufacturer['url'])
        scraper.scrape_and_write_data()


if __name__ == '__main__':
    get_data_by_mfg("NVIDIA")
    x = 3
# keys = list(multiple_dictionary.keys())
# for key in keys:
#     for i in range(len(multiple_dictionary[key])):
#         INPUT_START_URL = multiple_dictionary[key][i]
#         if __name__ == '__main__':
#             scraper = DigikeyScraper(INPUT_BROWSER_PATH, INPUT_START_URL)
#             scraper.scrape_and_write_data()
#
#
# list_of_directories = glob.glob("/Users/edenshrian/Desktop/Documents/Eden Shrian/Eden/Projects/SemiConnductors/*.csv")
# dates = []
# for i in range(len(list_of_directories)):
#     s = list_of_directories[i]
#     start = s.find("SemiConnductors/") + len("SemiConnductors/")
#     end = s.find(".csv")
#     substring = s[start:end]
#     dates.append(substring)
#
# list_of_dataframes = []
# for i in range(len(dates)):
#     if dates[i][:10] == datetime.now().strftime("%d-%m-%Y"):
#         df = pd.read_csv(list_of_directories[i])
#         list_of_dataframes.append(df)
#
# dataframe = pd.concat(list_of_dataframes)
