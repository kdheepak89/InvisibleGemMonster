# encoding: utf-8
"""
Reddit-Tumblr bot
"""
from __future__ import division

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
import tumblr


class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

def strip_tags(html):
    html = html.replace('</p>', '</p>\n')
    s = MLStripper()
    s.feed(html)
    return s.get_data()

class InvisibleGemMonster(object):
    """
    InvisibleGemMonster gets posts from tumblr page
    and posts them to Reddit

    InvisibleGemMonster will post to the following subreddits
        * /r/stevenuniverse
        * /r/gravityfalls
        * /r/overthegardenwall
        * /r/rickandmorty
        * /r/adventuretime
    """

    def __init__(self, **kwargs):
        self.config = kwargs
        self.logger = kwargs.pop('logger', logging.getLogger(__name__))
        self.logger.info('Initializing')

        # Create reddit agent
        self.reddit = praw.Reddit(user_agent=self.config['user_agent'])

        # Create tumblr agent
        self.tumblr = pytumblr.TumblrRestClient(
        self.config['tumblr_api_key_1'],
        self.config['tumblr_api_key_2'],
        self.config['tumblr_api_key_3'],
        self.config['tumblr_api_key_4']
        )

        # set default initial value for last_post_time for all blog
        for blog in tumblr.blog:
            self.config[blog] = {'last_post_time': '2015-01-01 00:00:00 GMT'}

        # login
        self.login(self.config['REDDIT_USERNAME'], self.config['REDDIT_PASSWORD'])

    def login(self, REDDIT_USERNAME, REDDIT_PASSWORD):
        """Logs into Reddit and Tumblr"""

        self.logger.info('Login to reddit')
        self.reddit.login(REDDIT_USERNAME, REDDIT_PASSWORD, disable_warning=True)

        self.logger.info('Login to tumblr')
        pass

    def is_new_post_exists(self, blog):
        self.logger.debug('Check if new post exists in %s', blog)
        if self.tumblr.posts(blog)['posts'] == []:
            return False

        # compare post time with last_post_time
        most_recent_post_date = self.tumblr.posts(blog)['posts'][0]['date']
        if time.strptime(self.config[blog]['last_post_time'], self.config['tumblr_date_format']) < time.strptime(most_recent_post_date, self.config['tumblr_date_format']):
            return(True)
        else:
            return(False)

    def is_post_about(self, check_tag, tags):
        for tag in tags:
            if check_tag.lower() in tag.lower():
                return(True)
            else:
                pass
        return(False)

    def get_new_post(self, blog):
        """
        Checks for new_post
        returns url and tags if new_post
        else returns False
        """

        if self.is_new_post_exists(blog[0]):
            self.logger.debug('New post')
            dictionary = self.tumblr.posts(blog[0])['posts'][0]

            self.config[blog[0]]['last_post_time'] = dictionary['date']

            last_post_time = self.config[blog[0]]['last_post_time']
            tumblr_date_format = self.config['tumblr_date_format']

            url = dictionary['post_url']

            month_str = time.strptime(last_post_time, tumblr_date_format).tm_mon
            day_str = time.strptime(last_post_time, tumblr_date_format).tm_mday

            title_date_format = '[%B %d]'
            post_time = '['+str(self.config['month_dict'][str(month_str)]) + ' ' + str(day_str) + ']'

            try:
                post_title = dictionary['caption']
                post_title = strip_tags(post_title)
                post_title = post_title.replace('\n', ' \n').split('\n')[0]
            except:
                post_title = ''

            tags = dictionary['tags']

            return({'url':url, 'tags': tags, 'post_title': post_title, 'post_time': post_time, 'blog': blog[0], 'subreddit': blog[1]})
        else:
            self.logger.debug('No new post')
            return(False)

    def submit_to(self, subreddit, url, tags, post_title, post_time, blog):
        try:
            self.logger.info("Trying to submit %s to %s", blog, subreddit)
            self.logger.debug(post_time)
            self.logger.debug(post_title)
            self.logger.debug(url)
            self.logger.debug(tags)
            if post_title == '':
                post_title = str(post_time)
            submission_object = self.reddit.submit(subreddit,
                                        post_title,
                                        url=str(url),
                                        text=None,
                                        captcha=None,
                                        save=False,
                                        send_replies=False)

            if self.is_post_about('spoiler', tags):
                submission_object.mark_as_nsfw()
            return submission_object
        except praw.errors.AlreadySubmitted, e:
            self.logger.error('Error occurred')
            self.logger.error("Post already submitted")
            pass
        except praw.errors.APIException, e:
            self.logger.error("\n")
            self.logger.error('Error occurred! %s', traceback.format_exc())
            self.logger.error("\n")
            raise
        except Exception, e:
            self.logger.error("\n")
            self.logger.error('Error occurred! %s', traceback.format_exc())
            self.logger.error("Post may not have been submitted")
            self.logger.error("\n")



    def submit(self, url, tags, post_title, post_time, blog, subreddit=False, test_subreddit=None):

        if test_subreddit:
            submission = self.submit_to(test_subreddit, url, tags, post_title, post_time, blog)
            return submission

        if subreddit == 'stevenuniverse':
            submission = self.submit_to(subreddit, url, tags, post_title, post_time, blog)
            submission.select_flair(flair_template_id='95e7a5ee-7da7-11e5-ae5f-0e7e1b254bb1')

        submission = self.submit_to(subreddit, url, tags, post_title, post_time, blog)

def get_from_environ(key):
    try:
        return os.environ[key]
    except:
        raise

def main():

    # Add streamhandler to root logger
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    formatter = logging.Formatter('%(message)s')
    ch.setFormatter(formatter)
    root.addHandler(ch)

    config_path = 'invisiblegemmonster.conf.example'
    logger = logging.getLogger(__name__)
    logger.info('Starting InvisibleGemMonster')

    with open(config_path) as config_file:
        config = json.load(config_file)

    for key in config:
        if config[key] == '':
            logger.info('Getting %s from environment', key)
            try:
                config[key] = get_from_environ(key)
            except Exception, e:
                logger.error("[ERROR]:", e)
        else:
            logger.info('Getting %s from file = %s', key, config[key])

    if config["logger_level"] == "DEBUG" or config["logger_level"] == "":
        root.setLevel(logging.DEBUG)
        ch.setLevel(logging.DEBUG)

    invisiblegemmonster = InvisibleGemMonster(**config)

    ticktock = 0
    maxticktock = 1
    while True:
        # logger.debug('Sleep for 1 second')
        # time.sleep(1)
        ticktock = ticktock + 1
        if int(ticktock / maxticktock) == 1:
            logger.info("Tick Tock = %s", str(ticktock))
            maxticktock = maxticktock*2

        for blog in tumblr.blog.items():

            try:
                new_post = invisiblegemmonster.get_new_post(blog)
                if new_post:
                    logger.info('We have a new post here!')
                    invisiblegemmonster.submit(**new_post)
                else:
                    logger.debug('No new post')
                    pass
            except praw.errors.InvalidCaptcha:
                logger.warning("Unable to post, Captcha issue")
            except Exception, e:
                logger.error('Error occurred! %s', traceback.format_exc())


if __name__ == '__main__':
    main()
