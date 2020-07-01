from mail import EmailProcessor
#import os
import logging
import time



#os.chmod('C:\\Users\\Murali\\AppData\\Local\\Temp\\',777)

log = r"C:\Developement\Projects\ForkIT\LogDir\fork_it_mail_" + \
    time.strftime("%Y%m%d-%H%M%S")+".log"
logging.basicConfig(filename=log, level=logging.DEBUG,
                    format='%(asctime)s %(levelname)s: %(message)s', datefmt='%d/%m/%Y %H:%M:%S')


SECRETS = {
    "email_aws_secret_access_key": ''
}

CONFIG = {
    "email_rules_file": r"C:\Developement\Projects\ForkIT\email_rules.json",
    "email_s3_inbox_url": "s3://fork-it-mail/Mails",
    "email_s3_attachment_dir": "INBOX",
    "email_aws_access_key_id": "",
    
}

email_proc = EmailProcessor(
    CONFIG["email_rules_file"],
    CONFIG["email_s3_inbox_url"],
    CONFIG["email_s3_attachment_dir"],
    CONFIG["email_aws_access_key_id"],
    SECRETS["email_aws_secret_access_key"])
results = []
	
results = email_proc.check_mail(update=True)