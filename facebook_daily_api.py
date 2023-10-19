import scrapy
import pandas as pd
from io import BytesIO
import requests
from selenium.webdriver import Firefox
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from tensorflow import keras
from fastapi.responses import JSONResponse
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from time import sleep
from datetime import datetime as dt, date
import urllib.request
import json
import os
import datetime
from PIL import Image
import numpy as np
from selenium.common.exceptions import NoSuchElementException
from fastapi import FastAPI
from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
app = FastAPI()
driver = Firefox()
from keras.models import load_model
current_datef = datetime.datetime.now().strftime("%Y-%m-%d")
directory_path = fr"D:\scraping\ecg-scraping\facebookreddit_scraper\{current_datef}"
if not os.path.exists(directory_path):
    os.makedirs(directory_path)
else:
    print(f"The directory '{directory_path}' already exists.")
file_path_origin = r'D:\scraping\ecg-scraping\facebookreddit_scraper\facebookreddit_scraper'
new_file_path=current_datef+ '.json'
file_path=file_path_origin+new_file_path
platform = "facebook"
# model_path = keras.models.load_model(r'D:\scraping\ecg-scraping\facebookreddit_scraper\classification_model\imageclassifier.h5')
class FacebookSpider(scrapy.Spider):
    name = "facebookv3"
    platform = "Facebook"
    model = load_model(r'D:\scraping\ecg-scraping\facebookreddit_scraper\classification_model\imageclassifier.h5')

    

    def is_ecg(self, image_src):
        img = Image.open(requests.get(image_src, stream=True).raw)
        img = img.convert('RGB')
        img = img.resize((256, 256))
        x = np.array(img)
        x = np.expand_dims(x, axis=0)
        pred = self.model.predict(x)[0]
        return bool(pred[0] < 0.5)
    def save_dictionary_to_json(self,dictionary, file_path):
        if os.path.isfile(file_path):
            with open(file_path, 'r') as json_file:
                try:
                    existing_data = json.load(json_file)
                except json.decoder.JSONDecodeError:
                    existing_data = []
            dictionary = [post for post in dictionary if post['image_src'] not in [data['image_src'] for data in existing_data]]
            existing_data.extend(dictionary)
        else:
            existing_data = dictionary

        with open(file_path, 'w') as json_file:
            json.dump(existing_data, json_file, indent=4)

    def get_first_image_urls(self, filepath):
        df = pd.read_csv(filepath, sep='\t', names=['urls'])
        add_word = lambda x: x + '/media'
        df['urls'] = df['urls'].apply(add_word)
        first_image = '(//*[@class="x1rg5ohu x5yr21d xl1xv1r xh8yej3"])[1]'
        first_image_url_list = []
        for url in df['urls']:
            driver.get(url)
            sleep(2)
            try:
                driver.save_screenshot("screenshot.png")
                but = driver.find_element(By.CSS_SELECTOR,
                                          'body > div.__fb-light-mode.x1n2onr6.x1vjfegm > div.x9f619.x1n2onr6.x1ja2u2z > div > div.x1uvtmcs.x4k7w5x.x1h91t0o.x1beo9mf.xaigb6o.x12ejxvf.x3igimt.xarpa2k.x1lytzrv.x1t2pt76.x7ja8zs.x1n2onr6.x1qrby5j.x1jfb8zj > div > div > div > div.xzg4506.x1l90r2v.x1pi30zi.x1swvt13 > div > div:nth-child(2)')
                but.click()
                login=driver.find_element(By.XPATH,'//*[@id=":r5:"]')
                login.send_keys('hassengharb@gmail.com')
                password=driver.find_element(By.XPATH,'//*[@id=":r7:"]')
                password.send_keys('22550887h')
                conncet=driver.find_element(By.XPATH,'/html/body/div[1]/div/div[1]/div/div[5]/div/div/div[1]/div/div[2]/div/div/div/div[2]/form/div/div[5]/div/div/div[1]/div/span/span')
                conncet.click()
               
                sleep(2)
            except NoSuchElementException as e:
                print("latest post added to the List")
            fb = driver.find_element(By.XPATH, first_image)
            sleep(1)
            fb.click()
            sleep(1)
            current_url = driver.current_url
            first_image_url_list.append(current_url)
            print(first_image_url_list)
            print("-" * 60, first_image_url_list)
            sleep(2)
                

        return first_image_url_list

    
    def start_requests(self):
        first_post_link = self.get_first_image_urls(r'D:/url_list.txt')
        current_date = date.today()
        for url in first_post_link:
            driver.get(url)
            sleep(10)
            comment_list_info = []
            game = driver.find_element(By.TAG_NAME, 'body')
            is_first = True
            image_links = []
            idx = 0
            yield scrapy.Request(url=url, callback=self.parse)
            while True:
                idx += 1
                is_first = False
                try:
                    post_text = driver.find_element(By.XPATH, "//div[@class='xyinxu5 x4uap5 x1g2khh7 xkhd6sd']")
                    post_age_element = None
                    try:
                        post_age_element = driver.find_element(By.XPATH, "(//span[contains(text(), ' h') and number(substring-before(text(), ' h')) >= 1 and number(substring-before(text(), ' h')) <= 23])[1]")
                    except NoSuchElementException:
                        print("the post is not from today,or its not  an image of ecg")
                        break
                    
                    post_age = post_age_element.text.split()[0]
                    post_age = int(post_age)
                    print("--" * 60, post_age)
                    if 1 <= post_age <= 23:
                        image_element = driver.find_element(By.XPATH, "//img[@data-visualcompletion='media-vc-image']")
                        comments_elements = driver.find_elements(By.XPATH, '//div[@dir="auto" and @style="text-align: start;"]')
                        image_src = image_element.get_attribute('src')
                        if image_src in image_links:
                            break
                        if self.is_ecg(image_src):
                            curr_date_time = dt.now().strftime("%Y_%m_%d_%H_%M_%S_%f")
                            image_name = f"{curr_date_time}.jpg"
                            image_file_path = f"{directory_path}/{image_name}"
                            urllib.request.urlretrieve(image_src, image_file_path)
                            image_links.append(image_src)
                            comment_list_info.append({
                                'image_name': image_name,
                                'title': post_text.text,
                                'image_src': image_src,
                                'comments': [comment.text for comment in comments_elements],
                                'platform': self.platform
                            })

                            self.save_dictionary_to_json(comment_list_info, file_path)

                        else:
                            print(f'{image_name} is not an ECG image')
                            sleep(1)
                    else:
                        break

                except NoSuchElementException as e:
                    print("Error occurred Continuing")
                game.send_keys(Keys.ARROW_RIGHT)
                sleep(1)

        driver.quit()
        print(f"Successfully scraped {len(first_post_link)} groups")
        return JSONResponse(content={"data": comment_list_info})


facebook_spider = FacebookSpider()

@app.get("/daily_facebook")
def scrape_reddit():
    data_list = list(facebook_spider.start_requests())  # Convert generator to list

  
    if os.path.isfile(file_path):
        with open(file_path, 'r') as json_file:
            file_content = json.load(json_file)
        return JSONResponse(content=file_content)