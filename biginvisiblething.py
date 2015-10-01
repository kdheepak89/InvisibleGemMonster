# encoding: utf-8
"""
Reddit-Tumblr bot
"""

from HTMLParser import HTMLParser
from pytz import timezone

import datetime
import json
import os
import praw
import pytumblr
import random
import time
import traceback
import logging
import sys

root = logging.getLogger()
root.setLevel(logging.INFO)

ch = logging.StreamHandler(sys.stdout)
ch.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
ch.setFormatter(formatter)
root.addHandler(ch)


class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

def strip_tags(html):
    s = MLStripper()
    s.feed(html)
    return s.get_data()

class BigInvisibleThing(object):
    """
    BigInvisibleThing gets posts from tumblr page
    and posts them to Reddit

    BigInvisibleThing will post to the following subreddits
        * /r/stevenuniverse
    """

    def __init__(self, **kwargs):
        self.config = kwargs

        logging.info('Initializing')
        self.reddit = praw.Reddit(user_agent=self.config['user_agent'])

        self.tumblr = pytumblr.TumblrRestClient(
        self.config['tumblr_api_key_1'],
        self.config['tumblr_api_key_2'],
        self.config['tumblr_api_key_3'],
        self.config['tumblr_api_key_4']
        )

        self.login(self.config['REDDIT_USERNAME'], self.config['REDDIT_PASSWORD'])

    def login(self, REDDIT_USERNAME, REDDIT_PASSWORD):
        """Logs into Reddit and Tumblr"""

        logging.info('Login to reddit')
        self.reddit.login(REDDIT_USERNAME, REDDIT_PASSWORD, disable_warning=True)

        logging.info('Login to tumblr')
        pass

    def is_new_post_exists(self):
        most_recent_post_date = self.tumblr.posts('discount-supervillain')['posts'][0]['date']
        if time.strptime(self.config['last_post_time'], self.config['tumblr_date_format']) < time.strptime(most_recent_post_date, self.config['tumblr_date_format']):
            return(True)
        else:
            return(False)

    def is_post_about(self, check_tag, tags):
        for tag in tags:
            if check_tag in tag:
                return(True)
            else:
                pass
        return(False)

    def get_new_post(self):
        """
        Checks for new_post
        returns url and tags if new_post
        else returns False
        """

        if self.is_new_post_exists():
            dictionary = self.tumblr.posts('discount-supervillain')['posts'][0]


            self.config['last_post_time'] = dictionary['date']

            last_post_time = self.config['last_post_time']
            tumblr_date_format = self.config['tumblr_date_format']

            url = dictionary['post_url']

            month_str = time.strptime(last_post_time, tumblr_date_format).tm_mon
            day_str = time.strptime(last_post_time, tumblr_date_format).tm_mday

            title_date_format = '[%B %d]'
            post_time = '['+str(self.config['month_dict'][str(month_str)]) + ' ' + str(day_str) + ']'

            try:
                post_title = dictionary['caption']
                post_title = strip_tags(post_title)
            except:
                post_title = ''

            tags = dictionary['tags']

            return({'url':url, 'tags': tags, 'post_title': post_title, 'post_time': post_time})
        else:
            return(False)

    def submit_to(self, subreddit, url, tags, post_title, post_time):
        try:
            submission_object = self.reddit.submit(subreddit,
                                        '[discount-supervillain] '+str(post_time)+' '+post_title,
                                        url=str(url),
                                        text=None,
                                        captcha=None,
                                        save=False,
                                        send_replies=False)

            if self.is_post_about('spoiler', tags):
                submission_object.mark_as_nsfw()
        except praw.errors.AlreadySubmitted, e:
            logging.info('Error occurred')
            logging.info("Post already submitted")
            pass
        except praw.errors.APIException, e:
            logging.error("\n")
            logging.error("[ERROR]:", e)
            logging.error("\n")
            raise
        except Exception, e:
            logging.error("\n")
            logging.error("[ERROR]:", e)
            logging.error("blindly handling any error")
            logging.error("\n")
            raise


    def submit(self, url, tags, post_title, post_time, test_subreddit=None):

        if test_subreddit:
            self.submit_to(test_subreddit, url, tags, post_title, post_time)

        if self.is_post_about('Steven Universe', tags):
            self.submit_to('stevenuniverse', url, tags, post_title, post_time)


def get_from_environ(key):
    try:
        return os.environ[key]
    except:
        raise

def main():

    logging.info('Starting BigInvisibleThing')
    config_path = 'biginvisiblething.conf.example'

    with open(config_path) as config_file:
        config = json.load(config_file)

    for key in config:
        if config[key] == '':
            logging.info('Getting %s from environment', key)
            config[key] = get_from_environ(key)

    biginvisiblething = BigInvisibleThing(**config)

    while True:
        logging.debug('Sleep for 1 second')
        time.sleep(1)
        if int(time.strftime('%M')) + int(time.strftime('%S')) == 0:
            logging.info("Tick Tock")
        try:
            new_post = biginvisiblething.get_new_post()

            if new_post:
                logging.info('We have a new post here!')
                biginvisiblething.submit(**new_post)
            else:
                logging.debug('Post already submitted')
                pass

        except Exception:
            raise
            logging.error('Error occurred! %s', traceback.format_exc())


if __name__ == '__main__':
    main()
