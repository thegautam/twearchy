import tweepy
import logging

from google.appengine.ext import db

MAX_LONG = ((2 ** 63) - 1)

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

class dbHandler():

    def get_newest_tweet_id(self, user_id):
        t = Tweet.all()
        t.filter("user_id =", user.id)
        t.sort("id")
        newest_tweet = t.get()

    def get_user(self, me):
        user = User.get_or_insert(key_name = str(me.id),
                                  id = me.id,
                                  screen_name = me.screen_name,
                                  lower_id = 1,
                                  upper_id = MAX_LONG)
        return user

    def get_location(self, status):
        location = None
        if status.place != None:
            latlong = status.place["bounding_box"]["coordinates"][0][0]
            location = str(latlong[1]) + "," + str(latlong[0])
        return location

    def save_missing_tweets(self, api, user):
        max_items = 200
        more_tweets = False
        upper_id = user.upper_id

        tweets =  tweepy.Cursor(api.user_timeline, 
                                since_id = str(user.lower_id),
                                max_id = str(user.upper_id - 1)).items(max_items)

        for status in tweets:
            more_tweets = True
            location = self.get_location(status)

            t = Tweet.get_or_insert(key_name = str(status.id),
                                    user_id = status.user.id,
                                    id = status.id,
                                    text = status.text,
                                    datetime = status.created_at,
                                    location = None)

            upper_id = min(upper_id, t.id)

        user.upper_id = upper_id
        user.put()

        return more_tweets

    def make_ids_current(self, user):
        t = Tweet.all()
        t.filter("user_id =", user.id)
        t.order("-id")
        last_tweet = t.get()

        user.upper_id = MAX_LONG
        user.lower_id = last_tweet.id

    def update_db(self, api):
        me = api.me()
        user = self.get_user(me)

        while self.save_missing_tweets(api, user):
            """ Nothing """

        self.make_ids_current(user)
