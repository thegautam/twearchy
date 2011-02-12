#!/usr/bin/env python

import logging
import tweepy
import string,re

from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template

from sessions import Session
from dbwrapper import dbHandler, Tweet

class MainHandler(webapp.RequestHandler):

  def process_status(self, tweet):
    text = tweet.text

    re_link = re.compile(r'(http[s]?://[\w._/\-\?=]*)', re.I)
    links_added = re_link.sub(r'<a href="\1" target="_blank">\1</a>', text)
    
    re_at = re.compile(r'((?<!\w)@\w+)', re.I)
    at_added = re_at.sub(r'<span class=atusr>\1</span>', links_added)

    href_added = '<a href=http://bing.com>%s</a>' % at_added

    meta = '<td><div class=mt>%s</div></td>' % tweet.datetime.ctime()
    final = "<tr>" + meta + "<td><div class=tweet>" + href_added + "</div></td></tr>"

    return final

  def get_trash_talk(self, count):
    message = 'Feedback'
    if count < 10:
      message = 'Hello, World!'
    elif count < 50:
      message = 'Welcome, Newbie!'
    elif count < 100:
      message = 'Speak up!'
    elif count < 500:
      message = 'Growing confidence?'
    elif count < 1000:
      message = 'Jabber Jabber...'
    else:
      message = 'Listen much?'

    return '<a class=h href="mailto:gkedia@conaytus.com?subject=Feedback Love">%s</a>' % message


  def get(self, mode=""):
    
    application_key = "fIPX8vbptBVFXe0QQPww4w" 
    application_secret = "t2lxYTZy5npenElfuAWV1uWVcoUQVCB2RENwx0uYRw4"
    callback_url = "%s/verify" % self.request.host_url

    auth = tweepy.OAuthHandler(application_key, application_secret, callback_url)
    self.session = Session()

    if mode == "":
      redirection_url = auth.get_authorization_url(signin_with_twitter=True)
      self.session['request_token'] = (auth.request_token.key, auth.request_token.secret)
      return self.redirect(redirection_url)
      
    if mode == "verify":
      auth_token = self.request.get("oauth_token")
      auth_verifier = self.request.get("oauth_verifier")

      request_token = self.session['request_token']
      auth.set_request_token(request_token[0], request_token[1])

      auth.get_access_token(auth_verifier)

      self.session['access_token'] = auth.access_token.key
      self.session['access_secret'] = auth.access_token.secret
      return self.redirect("%s/fetching" % self.request.host_url)

    if mode == "fetching":
      access_token = self.session['access_token']
      access_secret = self.session['access_secret']

      auth.set_access_token(access_token, access_secret)

      api = tweepy.API(auth)
      redirect_url = "%s/timeline" % self.request.host_url

      logging.info("username %s " % api.me().screen_name)

      template_values = {
        "username": api.me().screen_name,
        "redirect_url": redirect_url,
        }

      return self.response.out.write(template.render("fetching.html", template_values))

    if mode == "timeline":

      access_token = self.session['access_token']
      access_secret = self.session['access_secret']

      logging.info("%s %s" % (access_token, access_secret))
      auth.set_access_token(access_token, access_secret)

      api = tweepy.API(auth)

      dbhandler = dbHandler()
      dbhandler.update_db(api)

      content = ""
      count = 0

      t = Tweet.all()
      t.filter("user_id = ", api.me().id)
      t.order("-id")

      for status in t:
        html_status = self.process_status(status)
        content = content + html_status
        count = count + 1

      template_values = {
        "username": api.me().screen_name,
        "timeline": content,
        "count": count,
        "trash_talk": self.get_trash_talk(count)
        }

      return self.response.out.write(template.render("timeline.html", template_values))
                             
def main():
  application = webapp.WSGIApplication([('/(.*)', MainHandler)],
                                       debug=True)
  util.run_wsgi_app(application)


if __name__ == '__main__':
  main()
