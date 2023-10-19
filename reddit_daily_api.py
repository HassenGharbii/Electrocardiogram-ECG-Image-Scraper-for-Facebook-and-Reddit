import praw
import time
from io import BytesIO
from datetime import datetime as dt
import os
import requests
from prawcore.exceptions import Forbidden
import json
from tensorflow import keras
import numpy as np
from PIL import Image
from datetime import date
from datetime import datetime
import logging
from fastapi import FastAPI
from elasticsearch import Elasticsearch
import logstash
import smtplib
from email.mime.text import MIMEText

app = FastAPI()

current_date = dt.now().date()
subreddit_list = ["ECG","EKGs","EKG","askcardiology","ReadMyECG","PVCs","cardiology"]


class Logging(object):
    def __init__(self, logger_name='python-logger',
                 log_stash_host='localhost',
                 log_stash_upd_port=5959):
        self.logger_name = logger_name
        self.log_stash_host = log_stash_host
        self.log_stash_upd_port = log_stash_upd_port

    def get(self):
        logging.basicConfig(
            filename="zreddit_logfile.log",
            filemode="a",
            format="%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s",
            datefmt="%H:%M:%S",
            level=logging.INFO,
        )

        self.stderrLogger = logging.StreamHandler()
        logging.getLogger().addHandler(self.stderrLogger)
        self.logger = logging.getLogger(self.logger_name)
        self.logger.addHandler(logstash.LogstashHandler(self.log_stash_host,
                                                        self.log_stash_upd_port,
                                                        version=1))
        return self.logger




class RedditSpider:
    platform = "Reddit"
    current_datef = datetime.now().strftime("%Y-%m-%d")
    image_dir = fr"D:\scraping\ecg-scraping\facebookreddit_scraper\{current_datef}"
    model = keras.models.load_model(r'D:\scraping\ecg-scraping\facebookreddit_scraper\classification_model\imageclassifier.h5')
    def send_email(self,recipient, subject, message):
        sender = "hassengharb@gmail.com"  # Replace with your email address
        password = "otryocmkvbhehema"  # Replace with your email password

        msg = MIMEText(message)
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = recipient

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender, password)
        server.send_message(msg)
        server.quit()
    def __init__(self, subrd=None, posts_count=100, **kwargs):
        self.posts_count= int(posts_count)
        self.reddit = praw.Reddit(
            client_id='AJAJv2eZCgfPu7mduhJaJQ',
            client_secret='6ZP970QWwW7W4Ig0AizfiUenL1wqyw',
            user_agent='hassen ghatb',
            ratelimit_seconds=100,
            check_for_async=False

        )
    def count_records(json_data):
        count = 0
        # Assuming the JSON file contains an array of records
        for record in json_data:
            count += 1
        return count
    def is_ecg(self, image_url):
        response = requests.get(image_url)
        img = Image.open(BytesIO(response.content))
        img = img.convert('RGB')
        img = img.resize((256, 256))
        x = np.array(img)
        x = np.expand_dims(x, axis=0)
        pred = self.model.predict(x)[0]
        return bool(pred[0] < 0.5)


    def scrape_reddit(self):
        file_path_origin = r'D:\scraping\ecg-scraping\facebookreddit_scraper\facebookreddit_scraper'
        current_datef = datetime.now().strftime("%Y-%m-%d")
        new_file_path=current_datef+ '.json'
        filename=file_path_origin+new_file_path
        if os.path.isfile(filename):
            with open(filename, 'r') as f:
                data_list = json.load(f)
        else:
            data_list = []
        for subrd in subreddit_list:
            try:
                subreddit = self.reddit.subreddit(subrd)
                url = f'https://www.reddit.com/r/{subrd}/'
            except Forbidden:
                print(f"We\'ve been banned on r/{comment.subreddit}!")
            for post in subreddit.new(limit=self.posts_count):
                post_date = dt.fromtimestamp(post.created_utc).date()
                if post_date != current_date:
                    print(f"Post {post.id} is not from today, skipping")
                    continue
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
        # Send email notification
        
        recipient_email = "hassene5991@gmail.com"
        subject = "Scraping Report"
        message = f"Scraping completed. Number of images scraped for: {current_date} is :{len(data_list)}  "
        self.send_email(recipient_email, subject, message)

        return data_list


reddit_spider = RedditSpider()

@app.get("/daily_reddit")
def scrape_reddit():
    data_list = reddit_spider.scrape_reddit()

    # Return the scraped data
    return {"data": data_list}
