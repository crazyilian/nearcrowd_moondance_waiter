from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, UnexpectedAlertPresentException
from credentials import *

import os
import time
import logging


ALERT = True

logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


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


def add_localstorage_values(driver, vals):
    logger.debug("Passing local storage values: " + str(vals))
    for key in vals:
        driver.execute_script("window.localStorage.setItem(arguments[0], arguments[1]);", key, vals[key])
    logger.debug("Going to https://nearcrowd.com/v2")
    driver.get("https://nearcrowd.com/v2")


def checkIsPage(driver, name, unexpectedAlertVal=None):
    try:
        return "display: none" not in driver.find_element(By.ID, name).get_attribute("style")
    except (TypeError, AttributeError):
        return checkIsPage(driver, name, unexpectedAlertVal)
    except UnexpectedAlertPresentException:
        return unexpectedAlertVal


def handleAlert(driver):
    if (EC.alert_is_present()(driver)):
        alert = driver.switch_to.alert
        text = alert.text
        alert.accept()
        return text


def waitPageLoading(driver):
    logger.debug("Waiting Loading...")
    time.sleep(0.5)
    alert = handleAlert(driver)
    while checkIsPage(driver, "divLoading", True) or checkIsPage(driver, "divSubmitting"):
        time.sleep(0.1)
        alert_ = handleAlert(driver)
        alert = alert if alert_ is None else alert_
    time.sleep(0.5)
    return alert


def checkIsTask(driver):
    return driver.find_elements(By.CLASS_NAME, "CodeMirror") != []


if __name__ == "__main__":
    driver = start_driver()
    add_localstorage_values(driver, {
        "undefined_wallet_auth_key": f'{{"accountId":"{ACCOUNT_NAME}"}}',
        f"near-api-js:keystore:{ACCOUNT_NAME}:mainnet": PRIVATE_KEY,
        "v2tutorialseen42": "true"
    })

    if not ALERT:
        driver.execute_script("""window.alert_old = window.alert
                                 window.alert = function() {}""")

    cnt = 0
    while cnt := cnt + 1:
        logger.debug(f"Attempt {cnt}")

        waitPageLoading(driver)
        taskFound = False

        if checkIsPage(driver, "divTaskSelection"):
            logger.debug("Selecting taskset")
            driver.execute_script("selectTaskset(42)")
            waitPageLoading(driver)
            taskFound = checkIsTask(driver)

        if not taskFound:
            logger.debug("Claiming review")
            driver.execute_script("claimReview(42)")

            alert = waitPageLoading(driver)
            if ALERT and alert is None:
                logger.debug("Waiting for alert")
                try:
                    WebDriverWait(driver, 5).until(EC.alert_is_present())
                    alert = handleAlert(driver)
                except TimeoutException:
                    pass

            if alert is not None and 'outstanding' not in alert:
                if 'ratio' in alert:
                    logger.debug("RATIO LIMIT")
                elif 'access' in alert:
                    logger.debug("TIME LIMIT")
                else:
                    logger.debug(alert)
                print('\a')
                break

            taskFound = checkIsTask(driver)

        if not taskFound:
            continue

        print('\a')
        logger.debug("REVIEW CLAIMED")
        input('Press enter to wait new review: ')
        cnt = 0

    driver.quit()
