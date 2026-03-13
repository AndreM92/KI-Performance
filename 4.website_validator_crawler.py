
from selenium import webdriver
from selenium.webdriver.common.by import By
import selenium.webdriver.support.expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options

import requests
from bs4 import BeautifulSoup
from bs4.element import Comment
import lxml
import pandas as pd
from collections import OrderedDict

import os
from datetime import datetime, timedelta
import time
import re
from search_crawler_credentials import *
from ki_functions import *

chromedriver_path = r"C:\Users\andre\Documents\Python\chromedriver-win64\chromedriver.exe"
startpage = 'https://www.google.de'
file_path = r"C:\Users\andre\OneDrive\Desktop\Marketing\KI-Performance\KI-Performance Schuhe"
file_name = "distinct_brands_2026-03-11_19_28_30"
source_file = file_name + ".xlsx"
########################################################################################################################

# Start the driver and open a new page
def start_browser(webdriver, Service, chromedriver_path, my_useragent, headless=False, muted = False):
    # Open the Browser with a service object and an user agent
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument(f'user-agent={my_useragent}')
    if headless:
        chrome_options.add_argument('--headless')
    service = Service(chromedriver_path)
    driver = webdriver.Chrome(service=service, options=chrome_options)
    driver.maximize_window()
    driver.get(startpage)
    time.sleep(3)
    # Click through the first Cookie Banner
    cookiebuttons = driver.find_elements('xpath', "//*[contains(text(), 'ablehnen') or contains(text(), 'Ablehnen')]")
    if len(cookiebuttons) == 0 or 'youtube' in driver.current_url:
        driver.execute_script('window.scrollTo(0,document.body.scrollHeight)')
        time.sleep(2)
        cookiebuttons = driver.find_elements('xpath', '//button[contains(., "ablehnen")]')
    if len(cookiebuttons) == 0 and not 'instagram' in driver.current_url:
        cookiebuttons = driver.find_elements(By.TAG_NAME, 'button')
    if len(cookiebuttons) >= 1:
        for c in cookiebuttons:
            try:
                c.click()
            except:
                pass
    return driver, startpage


def go_to_page(driver, startpage):
    driver.get(startpage)
    time.sleep(3)
    # Click through the first Cookie Banner
    cookiebuttons = driver.find_elements('xpath', "//*[contains(text(), 'ablehnen') or contains(text(), 'Ablehnen')]")
    if len(cookiebuttons) == 0  or 'youtube' in driver.current_url:
        driver.execute_script('window.scrollTo(0,document.body.scrollHeight)')
        time.sleep(2)
        cookiebuttons = driver.find_elements('xpath', '//button[contains(., "ablehnen")]')
    if len(cookiebuttons) == 0 and not 'instagram' in driver.current_url:
        cookiebuttons = driver.find_elements(By.TAG_NAME,'button')
    if len(cookiebuttons) >= 1:
        for c in cookiebuttons:
            try:
                c.click()
            except:
                pass
    # Not the best solution so far
    cookiebuttons = driver.find_elements(By.TAG_NAME, "tiktok-cookie-banner")
    if len(cookiebuttons) >= 1 or 'tiktok.com' in driver.current_url:
        import pyautogui
        pyautogui.moveTo(1452,867) #1749,861
        pyautogui.click()
        time.sleep(1)


# Scrape the startpage
def scrape_startpage(driver, website):
    try:
        driver.get(website)
        time.sleep(4)
    except:
        return [], None, website
    actual_website = driver.current_url
    decline_str = "//*[contains(text(), 'ablehnen') or contains(text(), 'Ablehnen') or contains(text(), 'ABLEHNEN') or contains(text(), 'Verweigern')]"
    cookiebuttons = driver.find_elements('xpath', decline_str)
    if len(cookiebuttons) == 0:
        accept_str = "//*[contains(text(), 'akzeptieren') or contains(text(), 'AKZEPTIEREN') or contains(text(), 'einverstanden') or contains(text(), 'zulassen') or contains(text(), 'zustimmen') or contains(text(), 'annehmen') or contains(text(), 'accept')]"
        cookiebuttons = driver.find_elements('xpath', accept_str)
    if len(cookiebuttons) >= 1:
        for c in cookiebuttons:
            try:
                c.click()
            except:
                pass
        time.sleep(2)
    driver.execute_script("window.scrollBy(0,2500)", "")
    time.sleep(1)
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    pagetext = get_visible_text(re, soup)
    linklist = list(set(get_all_links(soup)))
    return linklist, pagetext, actual_website

########################################################################################################################
# Run the Crawler/ Scraper
if __name__ == '__main__':
    # Load the excel file with the required data
    # It should contain the company names and websites
    os.chdir(file_path)
    df_source = pd.read_excel(source_file)
    col_list = list(df_source.columns)
    # Start with an empty table and a number of rows you want so skip
    table = []

    driver, page = start_browser(webdriver, Service, chromedriver_path, my_useragent, False, False)

    start_ID = 0
    for ID, row in df_source.iterrows():
        if 'ID' in col_list:
            ID = row['ID']
        if ID < start_ID:
            continue

        brand = extract_text(re, row['Markenname'])
        company = extract_text(re, row['Firmenname'])
        website = str(row['Website'])
        linklist, pagetext, actual_website = scrape_startpage(driver, website)
        crawled_row = [ID, brand, company, website, actual_website, linklist, pagetext]
        table.append(crawled_row)
        print(crawled_row[:-1])

    # Dataframe
    header = ['ID', 'Markenname', 'Firmenname', 'Website', 'Landing-URL', 'Links', 'Startseite']
    df_website = pd.DataFrame(table, columns=header)
    dt_str_now = datetime.now().strftime("%Y-%m-%d_%H_%M_%S")
    recent_filename = 'Website_Links_' + dt_str_now + '.xlsx'
    try:
        # Create an Excel file
        df_website.to_excel(recent_filename + '.xlsx')
    except:
        # If there are problems with forbidden characters
        df_website.to_csv(recent_filename + '.csv', index=False)

    driver.quit()