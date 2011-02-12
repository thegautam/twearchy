import tweepy
import logging

from google.appengine.ext import db

MAX_LONG = ((2 ** 63) - 1)
MAX_FETCH = 200

class Tweet(db.Model):
    user_id = db.IntegerProperty(required=True)
    id = db.IntegerProperty(required=True)
    text = db.StringProperty(required=True, multiline=True)
    datetime = db.DateTimeProperty(required=True)
    latlong = db.GeoPtProperty()

    def to_string(self):
        string = str(self.user_id) + " " + str(self.id) + " "
        string = string + self.text + " " + str(self.datetime) + " "
        if self.latlong != None:
            string = string + " " + str(self.latlong)
        return string

class User(db.Model):
    id = db.IntegerProperty(required=True)
    screen_name = db.StringProperty(required=True)
    lower_id = db.IntegerProperty(required=True)
    upper_id = db.IntegerProperty(required=True)

    def get_last_tweet(self):
        t = Tweet.all()
        t.filter("user_id =", self.id)
        t.order("-id")
        return t.get()

    def make_ids_current(self):
        self.upper_id = MAX_LONG
        self.lower_id = self.get_last_tweet().id
        self.put()

class dbHandler():

    def get_user(self, me):
        return User.get_or_insert(key_name = str(me.id),
                                  id = me.id,
                                  screen_name = me.screen_name,
                                  lower_id = 1,
                                  upper_id = MAX_LONG)

    def get_location(self, tweet):
        location = None
        if tweet.place != None:
            latlong = tweet.place["bounding_box"]["coordinates"][0][0]
            location = str(latlong[1]) + "," + str(latlong[0])
        return location

    def save_missing_tweets(self, api, user):
        more_tweets = False
        upper_id = user.upper_id

        tweets =  tweepy.Cursor(api.user_timeline, 
                                since_id = str(user.lower_id),
                                max_id = str(user.upper_id - 1)).items(MAX_FETCH)

        for tweet in tweets:
            more_tweets = True
            location = self.get_location(tweet)

            t = Tweet.get_or_insert(key_name = str(tweet.id),
                                    user_id = tweet.user.id,
                                    id = tweet.id,
                                    text = tweet.text,
                                    datetime = tweet.created_at,
                                    location = None)

            upper_id = min(upper_id, t.id)

        user.upper_id = upper_id
        user.put()

        return more_tweets

    def update_db(self, api):
        user = self.get_user(api.me())

        while self.save_missing_tweets(api, user):
            """ Nothing """

        user.make_ids_current()
