import re
from enum import Enum
from typing import List
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
import datetime
import time
import pandas as pd
from csv import writer
import numpy as np
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

from ics_scraper.scrapers.utils import get_chrome_drive, wait
from ics_scraper.scrapers.scoring import scoring


class Duration(Enum):
    THREE_MONTHS = 3
    ONE_YEAR = 5


class IcsScraper:
    USERNAME = "ecrele1"
    PASSWORD = "ginger2016"
    MOCK_PRODUCT_ID = "r"
    LIST_OF_PRODUCTS = ["ESDA6V1LY"]
    #LIST_OF_PRODUCTS = ["QGE7320MC", "AD9830ASTZREEL", "AD9951YSVREEL7", "AD9913BCPZREEL7", "AD5934YRSZREEL7",
    #                    "AD9851BRSRL", "AD9838BCPZRL", "AD9837BCPZRL", "FST16090", "UFT20120"]
    CHROME_DRIVE_PATH = '/Users/hadarisraeli1/Desktop/Hadar/icsScraper/chromedriver'
    URL = "https://www.icsource.com/Home/index.aspx"
    TIME_TO_WAIT = 60
    TABLE_START_IND = 4

    def __init__(self):
        self.driver = get_chrome_drive(self.CHROME_DRIVE_PATH)
        self.initialize_icsource()

    def initialize_icsource(self):
        self.driver.get(self.URL)
        self.driver.find_element_by_css_selector("input[name='ctl00$logincontrol$txtUserName']").send_keys(self.USERNAME)
        self.driver.find_element_by_xpath("//input[@class='passwordhidden']").click()
        time.sleep(2.0)
        self.driver.find_element_by_xpath("//input[@name='ctl00$logincontrol$txtPassword']").send_keys(self.PASSWORD)
        self.driver.find_element_by_xpath("//*[@id='login']/div[3]").click()
        time.sleep(2.0)
        self.driver.find_element_by_xpath("//*[@id='txtPartNumber']").send_keys(self.MOCK_PRODUCT_ID)
        self.driver.find_element_by_xpath('//*[@id="divSingleSearch"]/table/tbody/tr/td[2]').click()
        time.sleep(2.0)

    def search_product(self, product_id):
        text_path = "//input[@class='txtSearchParts']"
        WebDriverWait(self.driver, self.TIME_TO_WAIT)\
            .until(EC.presence_of_element_located((By.XPATH, text_path)))

        self.driver.find_element_by_xpath(text_path).clear()
        self.driver.find_element_by_xpath(text_path).send_keys(product_id)
        time.sleep(1.0)
        self.driver.find_element_by_xpath(text_path).send_keys(Keys.RETURN)
        time.sleep(2.0)
        self.driver.maximize_window()

    #@wait(1.0)
    def get_country(self, index: int) -> List:
        try:
            return self.driver.find_element_by_xpath(
                        "/html/body/form/div[14]/div[3]/div[2]/div[2]/div[3]/div/table/tbody/tr[{}]/td[8]/div/span/img".format(
                            index)).get_attribute("title")
        except NoSuchElementException:
            pass

    #@wait(1.0)
    def get_company(self, index: int) -> List:
        try:
            return self.driver.find_element_by_xpath(
                "/html/body/form/div[14]/div[3]/div[2]/div[2]/div[3]/div/table/tbody/tr[{}]/td[10]/div".format(
                    index)).text
        except NoSuchElementException:
            pass

    #@wait(1.0)
    def get_mfg(self, index: int) -> List:
        try:
            text = self.driver.find_element_by_xpath(
                    "/html/body/form/div[14]/div[3]/div[2]/div[2]/div[3]/div/table/tbody/tr[{}]/td[5]/div".format(
                        index)).text
            if text:
                return text
            else:
                return 'N/A'

        except NoSuchElementException:
            pass


    #@wait(1.0)
    def get_quantity(self, index: int) -> List:
        try:
            return self.driver.find_element_by_xpath(
                    "/html/body/form/div[14]/div[3]/div[2]/div[2]/div[3]/div/table/tbody/tr[{}]/td[4]/div".format(
                        index)).text
        except NoSuchElementException:
            pass

    #@wait(1.5)
    def get_graph(self, product_id: str, duration=Duration.ONE_YEAR):
        self.driver.get(
            f"https://www.icsource.com/members/search/PartGraph.aspx?region=0&duration={duration.value}"
            f"&part={product_id}"
        )
        time.sleep(1.5)
        # self.driver.find_element_by_xpath(
        #     '/html/body/form/div[4]/table/tbody/tr[1]/td/table/tbody/tr/td[2]/div/table/tbody/tr/td[2]/a').click()
        # self.driver.find_element_by_xpath(
        #     '/html/body/form/div[1]/div/div/ul/li[6]').click()
        # time.sleep(3)

    def get_rate(self, product_id: str) -> int:
        self.get_graph(product_id=product_id)
        df = self.get_graph_dataframe()
        self.driver.back()
        time.sleep(2.0)
        return scoring(df)


    def parse_page_source(self):
        page_source = self.driver.page_source
        start_word = '"_dataSource":"['
        end_word = ',"_layout"'
        text_starts = page_source.find(start_word)
        text_ends = page_source.find(end_word)
        raw_data = page_source[text_starts + len(start_word): text_ends]
        semi_parsed_data = re.sub("""[^A-Za-z0-9{}(),'":]+""", ' ', raw_data)
        semi_parsed_data = re.sub(r'\bnew Date\b', '"', semi_parsed_data)

        magic_str = ", 0, 0, 0, 0)"

        while magic_str in semi_parsed_data:
            semi_parsed_data = semi_parsed_data.replace(magic_str, ')"')

        return [row + '}' for row in semi_parsed_data.split('},{')]



    def parse_page_str_to_values(self, page_search_values: str) -> list:
        date_index = 1
        count_index = 2
        parse_list = []
        for row in page_search_values:
            data_list = IcsScraper.get_row_data(row)
            data_list[date_index] = IcsScraper.date_fixer(data_list[date_index])
            data_list[count_index] = int(data_list[count_index])
            parse_list.append(data_list)

        return parse_list


    def get_graph_dataframe(self) -> pd.DataFrame:
        """
        Parses the graphs data from the icsource
        Returns:
            Dataframe of all the data points
        ## TODO: Parse the data in the dataframe
        """
        page_search_values = self.parse_page_source()
        page_values = self.parse_page_str_to_values(page_search_values)
        # a = [safe_parse(row) for row in page_search_values if safe_parse(row)]
        return pd.DataFrame(page_values, columns=['Part', 'Date', 'Searches'])


    def get_product_quantities(self, product_id: str) -> pd.DataFrame:
        self.search_product(product_id)
        self.driver.find_element_by_css_selector("input#divBTNStock").click()
        time.sleep(2.0)

        num_rows = len(self.driver.find_elements_by_xpath("//*[@id='searchResults']/tbody/tr"))
        df = pd.DataFrame()

        df['Quantities'] = [self.get_quantity(index=i) for i in np.arange(self.TABLE_START_IND, num_rows + 1)
                            if self.get_quantity(index=i)]
        df['MFGs'] = [self.get_mfg(index=i) for i in np.arange(self.TABLE_START_IND, num_rows + 1)
                      if self.get_mfg(index=i)]
        df['Companies'] = [self.get_company(index=i) for i in np.arange(self.TABLE_START_IND, num_rows + 1)
                           if self.get_company(index=i)]
        df['Countries'] = [self.get_country(index=i) for i in np.arange(self.TABLE_START_IND, num_rows + 1)
                           if self.get_country(index=i)]
        if not df.empty:
            score = self.get_rate(product_id)
            df['Rating'] = score
            if score > 1:
                print(f" ,score: {score}")
            else:
                print()
        else:
            print()

        return df

    # def get_product_quantities(self, product_id: str) -> pd.DataFrame:
    #
    #     df = pd.DataFrame()
    #     score = self.get_rate(product_id)
    #     if score > 0.5:
    #         self.search_product(product_id)
    #         self.driver.find_element_by_css_selector("input#divBTNStock").click()
    #         time.sleep(2.0)
    #
    #         num_rows = len(self.driver.find_elements_by_xpath("//*[@id='searchResults']/tbody/tr"))
    #
    #         df['Quantities'] = [self.get_quantity(index=i) for i in np.arange(self.TABLE_START_IND, num_rows + 1)
    #                             if self.get_quantity(index=i)]
    #         df['MFGs'] = [self.get_mfg(index=i) for i in np.arange(self.TABLE_START_IND, num_rows + 1)
    #                       if self.get_mfg(index=i)]
    #         df['Companies'] = [self.get_company(index=i) for i in np.arange(self.TABLE_START_IND, num_rows + 1)
    #                            if self.get_company(index=i)]
    #         df['Countries'] = [self.get_country(index=i) for i in np.arange(self.TABLE_START_IND, num_rows + 1)
    #                            if self.get_country(index=i)]
    #         if not df.empty:
    #
    #             df['Rating'] = score
    #             if score > 1:
    #                 print(f" ,score: {score}")
    #             else:
    #                 print()
    #         else:
    #             print()
    #     else:
    #         print()
    #     return df

    @classmethod
    def get_products_quantities(cls, products_id: List) -> pd.DataFrame:
        """
        Gets the quantities of a product list
        Args:
            products_id:  a list of product ids

        Returns:
            pd.Dataframe of products ids
        """
        ics_scraper = cls()
        list_of_dataframes = []
        for product_id in products_id:
            print(product_id, end=" ")
            df = ics_scraper.get_product_quantities(product_id)
            if not df.empty:
                df.loc[:, "Product_Id"] = product_id
                list_of_dataframes.append(df)
                IcsScraper.add_new_line_to_exist_csv(df, "/Users/hadarisraeli1/Downloads/test1.csv")
            time.sleep(1.5)



        # product_id_to_drop = []
        # for i in range(len(list_of_dataframes)):
        #     if len(list_of_dataframes[i]) >= 1:
        #         list_of_dataframes[i].loc[:, "Product ID"] = products_id[i]
        #     else:
        #         product_id_to_drop.append(products_id[i])

        inventory_df = pd.concat(list_of_dataframes)
        return inventory_df


    @staticmethod
    def date_fixer(date_str: str) -> datetime:
        year_index = 0
        month_index = 1
        day_index = 2
        date = date_str.split(',')
        date[month_index] = (int(date[month_index]) + 1)
        return datetime.datetime(int(date[year_index]), date[month_index], int(date[day_index]))


    @staticmethod
    def get_row_data(row: str) -> list:
        first_comma = 1
        last_comma = 1
        data_index = 1
        data_list = []
        interval = row.split(',', first_comma)
        date_value, search_value = (interval.pop()).rsplit(',', last_comma)
        interval.extend([date_value, search_value])
        for interval_data in interval:
            interval_data = interval_data.split(':')
            data_list.append(re.sub("[^A-Za-z0-9,]", "", interval_data[data_index]))

        return data_list


    @staticmethod
    def add_new_line_to_exist_csv(new_lines: pd.DataFrame, path: str):
        with open(path, 'a') as f_object:
            writer_object = writer(f_object)

            # Pass this file object to csv.writer()
            # and get a writer object
            for line in new_lines.values:

            # Pass the list as an argument into
            # the writerow()
                writer_object.writerow(line)

            # Close the file object
            f_object.close()



if __name__ == '__main__':
    stop = "SMA6J10A-TR"

    dataframe2 = pd.read_csv("/Users/hadarisraeli1/Downloads/digikey_data.csv")
    list_of_products = list(dataframe2[dataframe2['Supplier'] == 'STMicroelectronics']['Product_Model'].unique())
    index = list_of_products.index("L78L08ACD")
    list_of_products = list_of_products[index:]
    ics = IcsScraper.get_products_quantities(list_of_products)
    ics.to_csv("/Users/hadarisraeli1/Downloads/STMicroelectronics.csv")



