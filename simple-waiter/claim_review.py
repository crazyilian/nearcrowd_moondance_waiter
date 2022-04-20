from engine import main, logger
from selenium import webdriver
import requests
import os
import logging
import torpy.circuit


torpy.circuit.logger.setLevel(logging.ERROR)


def start_driver():
    logger.debug("Starting driver")
    chrome_options = webdriver.ChromeOptions()
    chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(executable_path=f'{os.getcwd()}/chromedriver', options=chrome_options)
    logger.debug("Going to nearcrowd.com")
    driver.get("https://nearcrowd.com")
    return driver


def start_requests_session():
    session = requests.session()
    pub_ip = session.get("https://ipinfo.io/ip").text
    logger.debug(f"Your IP is {pub_ip}")
    return session


driver = start_driver()
requests_session = start_requests_session()

main(driver, requests_session)
