import scrapy
import praw
import time
from io import BytesIO
from datetime import datetime as dt
import os
import requests
import json
from tensorflow import keras
import numpy as np
from PIL import Image


class RedditSpider(scrapy.Spider):
    platform="Reddit"                
    image_dir = 'images4'
    name = 'reddit'

    
    def __init__(self, subrd=None, posts_count=100000, **kwargs):
        self.subrds = subrd.split(',')  
        self.posts_count= int(posts_count)
        self.reddit = praw.Reddit(
            client_id='AJAJv2eZCgfPu7mduhJaJQ',
            client_secret='6ZP970QWwW7W4Ig0AizfiUenL1wqyw',
            user_agent='hassen ghatb',
            ratelimit_seconds=30,
            check_for_async=False

        )
        
        self.model = keras.models.load_model(r'/home/admin/Bureau/scraping-ecg/ecg-scraping/facebookreddit_scraper/classification_model/ecgclassifier.h5')

        super().__init__(**kwargs)
    def is_ecg(self, image_url):
        response = requests.get(image_url)
        img = Image.open(BytesIO(response.content))
        img = img.convert('RGB') 
        img = img.resize((256, 256)) 
        x = np.array(img)
        x = np.expand_dims(x, axis=0)
        pred = self.model.predict(x)[0]
        return bool(pred[0] < 0.5) 


    def start_requests(self):
        self.data = []
        for subrd in self.subrds:  
            subreddit = self.reddit.subreddit(subrd)
            url = f'https://www.reddit.com/r/{subrd}/'
            yield scrapy.Request(url, self.parse, meta={'subreddit': subreddit})
            
    def parse(self, response):
        filename = r'/home/admin/Bureau/scraping-ecg/ecg-scraping/facebookreddit_scraper/output4.json'
        if os.path.isfile(filename):
            with open(filename, 'r') as f:
                data_list = json.load(f)
        else:
            data_list = []
        subreddit = response.meta['subreddit']
        titles = []
        urls = []
        data={}
        comments = []
        for post in subreddit.hot(limit=self.posts_count):
            if post.url.endswith(".jpg") or post.url.endswith(".jpeg") or post.url.endswith(".png") or post.url.endswith(".gif") or post.url.endswith(".gifv"):
                titles = post.title
                urls = post.url
                if not self.is_ecg(urls):
                    print(f"Image {urls} is not an ECG, skipping")
                    continue
                post_comments = []   
                curr_date_time = dt.now().strftime("%Y_%m_%d_%H_%M_%S_%f")
                # Check if image_src already exists in the JSON file and skip downloading it
                if any(data['image_src'] == urls for data in data_list):
                    print(f"Image {urls} already exists in the JSON file, skipping download")
                    continue
                for comment in post.comments:
                    if not comment.author:
                        continue 
                    post_comments.append(comment.body)
                data = {
                    "image_name": f"{curr_date_time}.{urls.split('.')[-1]}",  # Save image name with extension
                    "title": titles,
                    "image_src": urls,
                    "comments": post_comments,
                    "platform": self.platform
                }
                data_list.append(data)
                os.makedirs(self.image_dir, exist_ok=True)
                # Check if image already exists in the image directory and skip downloading it
                image_name = f"{curr_date_time}.{urls.split('.')[-1]}"  # Use image name with extension
                image_path = os.path.join(self.image_dir, image_name)
                if os.path.exists(image_path):
                    print(f"Image {urls} already exists in the image directory, skipping download")
                else:
                    with open(filename, 'w') as f:
                        json.dump(data_list, f, indent=4)
                    for i in range(3):
                        try:
                            response = requests.get(urls)
                            response.raise_for_status()
                            with open(image_path, 'wb') as f:
                                f.write(response.content)
                            print(f"Image {urls} saved to {image_path}")
                            break

                        except requests.exceptions.RequestException:
                            if i == 2:
                                print(f"Failed to download image from URL {urls}")
                            else:
                                print(f"Retry {i+1} downloading image from URL {urls}")
