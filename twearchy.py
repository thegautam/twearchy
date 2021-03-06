#!/usr/bin/env python
import logging
import tweepy
import string,re
import traceback

from datetime import datetime, timedelta
from google.appengine.ext import webapp, db
from google.appengine.ext.webapp import util, template

from sessions import Session
from dbwrapper import dbHandler, Tweet

class MainHandler(webapp.RequestHandler):

  def format_html(self, str):
    out = string.replace(str, '  ', '&nbsp;&nbsp;')
    out = string.replace(out, '\n', '<br/>')
    return out

  def process_status(self, tweet, user):

    # Convert links to pointers.
    re_link = re.compile(r'(http[s]?://[\w._/\-\?=]*)', re.I)
    links_added = re_link.sub(r'<a href="\1" target="_blank">\1</a>', tweet.text)

    # Grey out user names.
    re_at = re.compile(r'((?<!\w)@\w+)', re.I)
    html_status = re_at.sub(r'<span class=atusr>\1</span>', links_added)

    # Get the local time of tweet.
    dt_offset = timedelta(seconds = user.utc_offset)
    str_format = '<div class=meta>%d %b %Y</div><div class=meta> %a %I:%M %p</div>'
    time_str = (tweet.datetime + dt_offset).strftime(str_format)

    # Get the link for the tweet.
    status_link = 'http://twitter.com/#!/%s/status/%s' % (user.screen_name, tweet.id)

    # Make the meta tag.
    html_meta = '<td width=100px><a href="%s" target="_blank">%s</a></td>' % (str(status_link), time_str)

    return  "<tr class=tweet>" + html_meta + "<td><div class=status>" + html_status  + "</div></td></tr>"

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

    return message

  def build_auth(self):
    application_key = "fIPX8vbptBVFXe0QQPww4w" 
    application_secret = "t2lxYTZy5npenElfuAWV1uWVcoUQVCB2RENwx0uYRw4"
    callback_url = "%s/verify" % self.request.host_url

    return tweepy.OAuthHandler(application_key, application_secret, callback_url)

  def handle_login(self):
    auth = self.build_auth()
    self.session = Session()
    redirection_url = auth.get_authorization_url(signin_with_twitter=True)
    self.session['request_token'] = (auth.request_token.key, auth.request_token.secret)
    return self.redirect(redirection_url)

  def handle_verify(self):
    auth = self.build_auth()
    self.session = Session()

    auth_token = self.request.get("oauth_token")
    auth_verifier = self.request.get("oauth_verifier")

    request_token = self.session['request_token']
    auth.set_request_token(request_token[0], request_token[1])

    auth.get_access_token(auth_verifier)

    self.session['access_token'] = auth.access_token.key
    self.session['access_secret'] = auth.access_token.secret
    return self.redirect("%s/fetching" % self.request.host_url)

  def get_fetching_message(self, count):
    if count == 0:
      return "Fetching your tweets before you can say hiybbprqag ..."
    elif count == 1:
      return "This may take a while, but it should be worth the wait."
    elif count == 3:
      return "We'll be faster the next time around. Promise!"
    elif count == 5:
      return "Still hustling forward, sit tight."
    elif count:
      return "We've fetched %d tweets. Are we there yet?" % ((count - 1) * 200)

  def fetching_html(self, me, fetching_count):
    redirect_url = "%s/timeline" % self.request.host_url

    template_values = {
      "username": me.screen_name,
      "redirect_url": redirect_url,
      "fetching_message": self.get_fetching_message(fetching_count),
      }

    return self.response.out.write(template.render("html/fetching.html", template_values))

  def handle_fetching(self):
    auth = self.build_auth()
    self.session = Session()

    access_token = self.session['access_token']
    access_secret = self.session['access_secret']

    auth.set_access_token(access_token, access_secret)

    api = tweepy.API(auth)
    me = api.me()

    logging.info("username %s " % me.screen_name)

    fetching_count = 0;
    self.session['fetching_count'] = fetching_count;

    return self.fetching_html(me, fetching_count)


  def handle_timeline(self):
    auth = self.build_auth()
    self.session = Session()

    access_token = self.session['access_token']
    access_secret = self.session['access_secret']

    logging.info("%s %s" % (access_token, access_secret))
    auth.set_access_token(access_token, access_secret)

    api = tweepy.API(auth)
    me = api.me()

    dbhandler = dbHandler()
    more_tweets = dbhandler.update_db(api)

    if (more_tweets):
      fetching_count = self.session['fetching_count'] + 1
      self.session['fetching_count'] = fetching_count
      return self.fetching_html(me, fetching_count)

    content = ""
    count = 0

    t = Tweet.all()
    t.filter("user_id = ", me.id)
    t.order("-id")

    for status in t:
      html_status = self.process_status(status, me)
      content = content + html_status
      count = count + 1

    template_values = {
      "username": me.screen_name,
      "timeline": content,
      "count": count,
      "trash_talk": self.get_trash_talk(count)
      }

    return self.response.out.write(template.render("html/timeline.html", template_values))


  def handle_request(self, mode=""):
    
    if mode == "":
      return self.response.out.write(template.render("html/landing.html", None))

    if mode == "login":
      return self.handle_login()
      
    if mode == "verify":
      return self.handle_verify()

    if mode == "fetching":
      return self.handle_fetching()

    if mode == "timeline":
      return self.handle_timeline()

  def handle_exception(self, exception, message):
      logging.exception(exception)
      template_values = {
        "traceback": self.format_html(exception),
        "message": message,
        }
      return self.response.out.write(template.render("html/yaa-utzah.html", template_values))

  def get(self, mode=""):

    try:
      return self.handle_request(mode)
    except Exception:
      exception = traceback.format_exc()
      self.handle_exception(exception, "We've hit some turbulence. Our engineers are on it as we speak.")

def main():
  application = webapp.WSGIApplication([('/(.*)', MainHandler)],
                                       debug=True)
  util.run_wsgi_app(application)

if __name__ == '__main__':
  main()
