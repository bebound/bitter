import os
import smtplib
import subprocess


class Mail():
    def __init__(self, email, subject, message):
        self.email = email
        self.subject = subject
        self.message = message

    # def send(self):
    #     subprocess.call(
    #         "curl -s --user 'api:key-5fe496b99081a02311959b196909c428' https://api.mailgun.net/v3/sandboxe3f5345622d54fb8b183893d8e74a837.mailgun.org/messages  -F from='Excited User <mailgun@sandboxe3f5345622d54fb8b183893d8e74a837.mailgun.org>'   -F to={0}  -F subject='{1}' -F text='{2}'".format(
    #             self.email, self.subject, self.message), shell=True, stdout=open(os.devnull, 'wb'))

    def send(self):
        server=smtplib.SMTP('smtp.cse.unsw.edu.au')
        content='Subject: {0}\n\n{1}'.format(self.subject,self.message)
        server.sendmail('bitter@bitter.com',self.email,content)
        server.quit()