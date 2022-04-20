from engine import main, logger
from selenium import webdriver
import requests
import sys
import os
import logging
from torpy.cli.socks import register_logger, TorClient, SocksServer
import torpy.circuit
import threading


torpy.circuit.logger.setLevel(logging.ERROR)


def start_tor_proxy(port):
    ip = '127.0.0.1'

    def runProxy(event, stopped):
        try:
            # register_logger(None)
            tor = TorClient()
            with tor.create_circuit(2) as circuit, SocksServer(circuit, ip, port) as socks_serv:
                event.set()
                if not stopped():
                    socks_serv.start()
        except OSError as e:
            if e.errno == 98:
                logger.debug("PORT IS ALREADY IN USE")

    logger.debug("Starting new tor proxy...")
    threadStopped = False
    proxyStartedEvent = threading.Event()
    proxyThread = threading.Thread(target=runProxy, args=[proxyStartedEvent, lambda: threadStopped], daemon=True)
    proxyThread.start()

    if not proxyStartedEvent.wait(10):
        threadStopped = True
        logger.debug('Proxy timed out')
        return
    else:
        logger.debug("Proxy started successfully")
        return f"socks5://{ip}:{port}"


def start_proxy_driver(addr):
    logger.debug("Starting driver")
    chrome_options = webdriver.ChromeOptions()
    chrome_options.binary_location = os.environ.get("GOOGLE_CHROME_BIN")
    # chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument(f'--proxy-server={addr}')
    driver = webdriver.Chrome(executable_path=f'{os.getcwd()}/chromedriver', options=chrome_options)
    logger.debug("Going to nearcrowd.com")
    driver.get("https://nearcrowd.com")
    return driver


def start_requests_session(addr):
    session = requests.session()
    session.proxies = {
        'http': addr,
        'https': addr
    }
    pub_ip = session.get("https://ipinfo.io/ip").text
    logger.debug(f"Your IP is {pub_ip}")
    return session


PORT = int(sys.argv[2])

proxy_addr = None
while proxy_addr is None:
    proxy_addr = start_tor_proxy(PORT)

driver = start_proxy_driver(proxy_addr)
requests_session = start_requests_session(proxy_addr)

main(driver, requests_session)
