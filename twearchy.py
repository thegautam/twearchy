#!/usr/bin/env python

import logging
import tweepy
import string,re

from google.appengine.ext import webapp
from google.appengine.ext.webapp import util, template

from sessions import Session

class MainHandler(webapp.RequestHandler):

  def repl_link(self, m):
    return m.group(1) + "<a href=\"" + m.group(2) + "\" target=\"_blank\">" + m.group(2) + "</a>" + m.group(3)

  def process_status(self, text):
    re_link = re.compile(r"""
        (.*?)          # Part before link
        (http[s]?://   # Link start
        [\w._/\-\?=]*) # Actual link including dots
        (.*?)""",      # Part after link
        re.IGNORECASE | re.VERBOSE)

    links_added = re_link.sub(self.repl_link, text)

    final = "<tr><td>" + links_added + "</td></tr>"

    return final

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
      return self.redirect("%s/pulling" % self.request.host_url)

    if mode == "pulling":
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

      return self.response.out.write(template.render("pulling.html", template_values))

    if mode == "timeline":
      timeline_url = "http://twitter.com/statuses/user_timeline.xml"

      access_token = self.session['access_token']
      access_secret = self.session['access_secret']

      logging.info("%s %s" % (access_token, access_secret))
      auth.set_access_token(access_token, access_secret)

      api = tweepy.API(auth)
      content = ""
      for status in tweepy.Cursor(api.user_timeline).items(500):
        html_status = self.process_status(status.text)
        content = content + html_status

      template_values = {
        "username": api.me().screen_name,
        "timeline": content
        }

      return self.response.out.write(template.render("timeline.html", template_values))
                             
def main():
  application = webapp.WSGIApplication([('/(.*)', MainHandler)],
                                       debug=True)
  util.run_wsgi_app(application)


if __name__ == '__main__':
  main()
