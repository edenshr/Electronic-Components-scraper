import time
import json.decoder

from selenium import webdriver


def get_chrome_drive_options():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('disable-infobars')
    chrome_options.add_argument('--disable-notifications')
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_experimental_option('useAutomationExtension', False)
    chrome_options.add_argument('--disable-popup-blocking')
    return chrome_options


def get_chrome_drive(drive_path):
    options = get_chrome_drive_options()
    driver = webdriver.Chrome(executable_path=drive_path, options=options)
    return driver


def wait(secs):
    def decorator(func):
        def wrapper(*args, **kwargs):
            time.sleep(secs)
            return func(*args, **kwargs)

        return wrapper

    return decorator


def safe_parse(string_to_parse):
    try:
        return json.loads(string_to_parse)
    except json.decoder.JSONDecodeError:
        return None

