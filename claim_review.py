from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import UnexpectedAlertPresentException
from credentials import *
import requests
import json
import datetime
import sys
import os
import time
import logging


logging.basicConfig()
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
requests.packages.urllib3.disable_warnings()


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


def waitPageLoading(driver):
    logger.debug("Waiting Loading...")
    time.sleep(0.5)
    while "display: none" not in driver.find_element(By.ID, "divLoading").get_attribute("style"):
        time.sleep(0.3)
    time.sleep(0.5)


def string2time(tm):
    hh, mm, ss = map(int, tm.split(':'))
    sec = hh * 60 * 60 + mm * 60 + ss
    dt = datetime.datetime.now() + datetime.timedelta(seconds=sec)
    return dt


def translateTime(dic, key):
    if key in dic:
        dic[key] = string2time(dic[key])


def getHash(driver):
    hsh = driver.execute_script("""
        return await window.contract.account.signTransaction('app.nearcrowd.near', [nearApi.transactions.functionCall('v2', {}, 0, 0)]).then(arr => {
            let encodedTx = btoa(String.fromCharCode.apply(null, arr[1].encode()));
            return encodeURIComponent(encodedTx);
        }).catch(errorOut);
    """)
    return hsh


def prettifyStatus(status):
    logger.debug(f"Prettifying {str(status)}")
    try:
        status = json.loads(status)
        translateTime(status, 'can_claim_task_in')
        translateTime(status, 'can_claim_review_in')
        translateTime(status, 'time_left')
    except ValueError:
        pass
    return status


def getPageResponse(driver, page):
    hsh = getHash(driver)
    url = f"https://nearcrowd.com/v2/{page}/{hsh}"
    resp = requests.get(url, verify=False)
    return resp


def getStatus(driver):
    logger.debug("Getting status")
    res = getPageResponse(driver, 'taskset/42').text
    status = prettifyStatus(res)
    return status


def claimReview(driver):
    logger.debug("Claiming review")
    res = getPageResponse(driver, 'claim_review/42').text
    return res


def hasWork(status):
    return status.get('status') in ('has_review', 'has_task')


def goToTaskPage(driver):
    driver.execute_script('selectTaskset(42)')


if __name__ == "__main__":
    driver = start_driver()
    add_localstorage_values(driver, {
        "undefined_wallet_auth_key": f'{{"accountId":"{ACCOUNT_NAME}"}}',
        f"near-api-js:keystore:{ACCOUNT_NAME}:mainnet": PRIVATE_KEY,
        "v2tutorialseen42": "true"
    })

    # driver.execute_script("""window.alert_old = window.alert
    #                          window.alert = function() {}""")

    waitPageLoading(driver)
    goToTaskPage(driver)
    while True:
        try:
            status = getStatus(driver)
            cnt = 0
            while not hasWork(status):
                cnt += 1
                logger.debug(f"Attempt {cnt}")
                res = claimReview(driver)

                if res == 'no_reviews':
                    logger.debug("Unsuccessful")
                elif 'user_task_id' in res:
                    logger.debug("Review claimed")
                    status = prettifyStatus(res)
                    status['status'] = 'has_review'
                elif res == 'need_more_tasks':
                    print('\a')
                    logger.debug("RATIO LIMIT")
                    sys.exit(0)
                elif res == 'no_access':
                    print('\a')
                    logger.debug("TIME LIMIT")
                    goToTaskPage(driver)
                    status = getStatus(driver)
                    endtime = status['can_claim_review_in']
                    waitsec = (endtime - datetime.datetime.now()).seconds
                    waitsec = max(0, waitsec)
                    logger.debug(f"Wait until {endtime.strftime('%H:%M:%S')} ({waitsec // 60} minutes)")
                    time.sleep(waitsec)
                else:
                    print('\a')
                    logger.debug('UNKNOWN CLAIM REVIEW STATUS:')
                    logger.debug(res)

            print('\a')
            goToTaskPage(driver)

            if status['status'] == 'has_review':
                logger.debug("REVIEW IS ACTIVE")
            else:
                logger.debug('TASK IS ACTIVE')
            input('Press enter to wait new review: ')
        except UnexpectedAlertPresentException as e:
            logger.debug(f'Unexpected Alert: {e.alert_text}')
            logger.debug('Proceeding...')
        except Exception as e:
            print('\a')
            logger.debug('UNKNOWN EXCEPTION IN SCRIPT')
            logger.exception(e)
            logger.debug('Waiting 5 sec')
            time.sleep(5)
            logger.debug('Proceeding...')
