import scrapy
import pandas as pd
from io import BytesIO
import requests
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from tensorflow import keras
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.options import Options
from time import sleep
from datetime import datetime as dt
import urllib.request
import json
import os 
from PIL import Image
import numpy as np
from selenium.common.exceptions import NoSuchElementException


file_path = r'/home/admin/Bureau/scraping-ecg/ecg-scraping/facebookreddit_scraper/facebookreddit_scraper/6-15-2023.json'
platform="facebook"

model_path = r'/home/admin/Bureau/scraping-ecg/ecg-scraping/facebookreddit_scraper/classification_model/ecgclassifier.h5'
options = Options()
options.headless = True
driver = webdriver.Firefox("/home/admin/Bureau/scraping-ecg/ecg-scraping/firefoxdriver", options = options) 

def save_dictionary_to_json(dictionary, file_path):
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
        json.dump(existing_data, json_file , indent=4)


class FacebookSpider(scrapy.Spider):
    name = "facebook"
    platform="Facebook"
    model = keras.models.load_model(model_path)

    def is_ecg(self, image_src):
        img=Image.open(requests.get(image_src, stream=True).raw)
        img = img.convert('RGB') 
        img = img.resize((256, 256)) 
        x = np.array(img)
        x = np.expand_dims(x, axis=0)
        pred = self.model.predict(x)[0]
        return bool(pred[0] < 0.5) 
    def get_first_image_urls(self,filepath):
        df = pd.read_csv(filepath, sep='\t', names=['urls'])
        add_word = lambda x: x + '/media'
        df['urls'] = df['urls'].apply(add_word)       
        first_image = '(//*[@class="x1rg5ohu x5yr21d xl1xv1r xh8yej3"])[1]'
        first_image_url_list = []
        for url in df['urls']:
            driver.get(url)
            sleep(10) 
            try:
                # WebDriverWait(driver, 30).until(EC.invisibility_of_element_located((By.XPATH, "//div[contains(@class, '__fb-light-mode') and contains(@class, 'x1qjc9v5') and contains(@class, 'x9f619') and contains(@class, 'x78zum5') and contains(@class, 'xdt5ytf') and contains(@class, 'x1iyjqo2') and contains(@class, 'xl56j7k') and contains(@class, 'xshlqvt')]")))
                # but=WebDriverWait(driver, 20).until(By.XPATH,'//div[@class="x1n2onr6 x1ja2u2z x78zum5 x2lah0s xl56j7k x6s0dn4 xozqiw3 x1q0g3np xi112ho x17zwfj4 x585lrc x1403ito x972fbf xcfux6l x1qhh985 xm0m39n x9f619 xn6708d x1ye3gou x1qhmfi1 x1r1pt67"]')
                driver.save_screenshot("screenshot.png")
                but=driver.find_element(By.CSS_SELECTOR,'body > div.__fb-light-mode.x1n2onr6.x1vjfegm > div.x9f619.x1n2onr6.x1ja2u2z > div > div.x1uvtmcs.x4k7w5x.x1h91t0o.x1beo9mf.xaigb6o.x12ejxvf.x3igimt.xarpa2k.x1lytzrv.x1t2pt76.x7ja8zs.x1n2onr6.x1qrby5j.x1jfb8zj > div > div > div > div.xzg4506.x1l90r2v.x1pi30zi.x1swvt13 > div > div:nth-child(2)')
                but.click()
                sleep(6)
            except NoSuchElementException as e:
                print("Error occurred. Continuing...")
            fb = driver.find_element(By.XPATH, first_image)
            sleep(2)
            fb.click()
            sleep(2)
            current_url = driver.current_url
            first_image_url_list.append(current_url)
            print("-"*60 ,first_image_url_list)
            
            
        return first_image_url_list
 

    
    def start_requests(self):
            first_post_link = self.get_first_image_urls('/home/admin/Bureau/scraping-ecg/ecg-scraping/facebookreddit_scraper/url_list.txt')   
            for url in first_post_link:
                driver.get(url)
                sleep(10)
                comment_list_info = []
                game = driver.find_element(By.TAG_NAME, 'body')
                is_first = True
                image_links = []
                idx = 0
                yield scrapy.Request(url=url, callback=self.parse)
                while(True):
                        idx += 1
                        is_first = False                  
                        try:   
                                post_text=driver.find_element(By.XPATH ,"//div[@class='xyinxu5 x4uap5 x1g2khh7 xkhd6sd']")
                                image_element = driver.find_element(By.XPATH, "//img[@data-visualcompletion='media-vc-image']")
                                comments_elements = driver.find_elements(By.XPATH, '//div[@dir="auto" and @style="text-align: start;"]') 
                                image_src = image_element.get_attribute('src') 

                                if image_src in image_links:
                                        break                   
                                if image_src:
                                        curr_date_time = dt.now().strftime("%Y_%m_%d_%H_%M_%S_%f")
                                        image_name = f"{curr_date_time}.jpg"
                                        image_file_path = f"./test2/{image_name}" 
                                        urllib.request.urlretrieve(image_src, image_file_path)
                                        image_links.append(image_src)

                                        if self.is_ecg(image_src):
                                            comment_list_info.append({
                                                        'image_name':image_name,
                                                        'title':post_text.text,
                                                        'image_src' : image_src,
                                                        'comments': [comment.text for comment in comments_elements],
                                                        'platform':self.platform
                                                })
                                            save_dictionary_to_json(comment_list_info, file_path)
                                        else:
                                            print(f'{image_name} is not an ECG image')
                                            os.remove(image_file_path)

                                        sleep(1)

                        except NoSuchElementException as e:
                                print("Error occured Continuing")
                        game.send_keys(Keys.ARROW_RIGHT)
                        sleep(1)
            

            driver.quit()
            print(f"successfully scraped {len(first_post_link)} groups")
