from selenium.webdriver.common.by import By
from selenium.common.exceptions import UnexpectedAlertPresentException
from credentials import *
import requests
import json
import datetime
import sys
import time
import logging


logging.basicConfig(format="%(asctime)s | %(name)s | %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger(ACCOUNT_NAME.removesuffix(".near").removesuffix(".crowdforces"))
logger.setLevel(logging.DEBUG)
requests.packages.urllib3.disable_warnings()
request_session = None


def set_title(driver):
    driver.execute_script(f"document.title = '{ACCOUNT_NAME}'")


def add_localstorage_values(driver, vals):
    logger.debug("Passing local storage values: " + str(vals))
    for key in vals:
        driver.execute_script("window.localStorage.setItem(arguments[0], arguments[1]);", key, vals[key])
    logger.debug("Going to https://nearcrowd.com/v2")
    driver.get("https://nearcrowd.com/v2")


def waitPage(driver, div):
    logger.debug(f"Waiting {div.removeprefix('div')}...")
    time.sleep(0.5)
    while "display: none" not in driver.find_element(By.ID, div).get_attribute("style"):
        time.sleep(0.3)
    time.sleep(0.5)
    set_title(driver)


def waitPageLoading(driver):
    waitPage(driver, "divLoading")


def waitPageSubmitting(driver):
    waitPage(driver, "divSubmitting")


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
    resp = requests_session.get(url, verify=False)
    return resp


def getStatus(driver):
    logger.debug("Getting status")
    res = getPageResponse(driver, 'taskset/42').text
    status = prettifyStatus(res)
    set_title(driver)
    return status


def claimReview(driver):
    logger.debug("Claiming review")
    res = getPageResponse(driver, 'claim_review/42').text
    set_title(driver)
    return res


def hasWork(status):
    return status.get('status') in ('has_review', 'has_task')


def goToTaskPage(driver):
    driver.execute_script('selectTaskset(42)')
    set_title(driver)


def main(driver, requests_session_):
    global requests_session
    requests_session = requests_session_

    add_localstorage_values(driver, {
        "undefined_wallet_auth_key": f'{{"accountId":"{ACCOUNT_NAME}"}}',
        f"near-api-js:keystore:{ACCOUNT_NAME}:mainnet": PRIVATE_KEY,
        "v2tutorialseen42": "true"
    })
    # driver.execute_script("""window.alert_old = window.alert
    #                          window.alert = function() {}""")

    waitPageLoading(driver)
    goToTaskPage(driver)
    cnt = 0
    while True:
        try:
            status = getStatus(driver)
            while not hasWork(status):
                time.sleep(5)
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
            waitPageSubmitting(driver)
            cnt = 0
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
