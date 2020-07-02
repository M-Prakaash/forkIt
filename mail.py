#!/usr/bin/env python2.7

from __future__ import absolute_import
from __future__ import print_function
from html.parser import HTMLParser
import io
from datetime import datetime
import email
import email.header
import json
import os
import re
import tempfile
import time
import zipfile
import logging
import requests

#from frplib.log import LOG
from util import fmt
from util import strip_newlines
from util import to_list
from util import unquote
from util import Error
import s3

def extract_forwarded_email(message):
    try:
        forwarded = [p for p in message.get_payload() if p.get_content_type() == "message/rfc822"]
    except Exception as _:
        raise Error("forwarded attachment expected but missing")
    if not forwarded:
        raise Error("forwarded attachment expected but missing")
    if len(forwarded) > 1:
        # NOTE: all emails should be placed with the 'Forward as
        # Attachment' option in outlook. so there should only be a single
        # attachment containing the forwarded email
        raise Error("expected 1 forwarded attachment. got", len(forwarded))
    return forwarded[0].get_payload()[0]


def decode_email_header(header, charset="utf8"):
    """
    returns an email header as a unquoted unicode string
    """
    dec = email.header.decode_header(header)[0]
    hdr = dec[0]
    if dec[1] is not None:
        hdr = hdr.dec[1]
    return unquote(hdr)

def decode_email_address(address, charset="utf8"):
    """
    returns an email address as a unquoted unicode string
    """
    name = decode_email_header(address[0])
    addr = address[1]
    addr = "<" + addr + ">"
    if not name:
        return addr
    return name + " " + addr

def clean_link(text):
    return re.sub(r'\s+', ' ', strip_newlines(text)).strip()

class LinkParser(HTMLParser):
    curr = None
    links = []
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            for a in attrs:
                if a[0] == "href":
                    self.curr = a[1]
                    break

    def handle_endtag(self, tag):
        self.curr = None

    def handle_data(self, data):
        if self.curr is not None:
            self.links.append([clean_link(data), self.curr])

class Email(object):
    def __init__(self, key, msg, original_date=None):
        self.key = key
        self.text = ""
        self.html = ""
        self.attachments = []
        self.links = []
        self.date = original_date
        self.subject = None
        self.fr = None
        self.to = None
        self.cc = None
        if msg:
            self.date = email.utils.parsedate(msg.get("Date")) or original_date
            charset = msg.get_content_charset() or "utf8"
            self.subject = strip_newlines(decode_email_header(msg.get("Subject"), charset))
            fr_addr = email.utils.getaddresses(msg.get_all("From", []))
            to_addr = email.utils.getaddresses(msg.get_all("To", []))
            cc_addr = email.utils.getaddresses(msg.get_all("Cc", []))
            self.fr = "; ".join([decode_email_address(f, charset) for f in fr_addr])
            self.to = "; ".join([decode_email_address(t, charset) for t in to_addr])
            self.cc = "; ".join([decode_email_address(t, charset) for t in cc_addr])
        self.errors = []
        self.destinations = []

    def __str__(self):
        return self.info()

    def info(self, include_links=True):
        atch_names = [get_attachment_name(a) for a in self.attachments]
        lines = [
            fmt(self.key),
            fmt("From         :", self.fr),
            fmt("To           :", self.to),
            fmt("CC           :", self.cc),
            fmt("Subject      :", self.subject),
            fmt("Date         :", self.date),
            fmt("Attachments  :", atch_names),
        ]
        if include_links:
            lines.append(fmt("Links        :", self.links))
        if self.errors:
            for error in self.errors:
                lines.append(fmt("ERROR        :", error))
        else:
            lines.append(fmt("OKAY         :", dest=self.destinations[0]))
        return "\n" + "\n".join(lines)

    def validate(self, destinations):
        self.destinations = destinations
        # edge-case
        if len(destinations) > 1:
            self.errors.append(fmt("multiple destinations found:", destinations))
        if not destinations:
            self.errors.append("no destinations found")
        if not self.date:
            self.errors.append("unable to extract received date")
        if not self.attachments:
            self.errors.append("no attachments found")


def parse_email(key, file_obj, forwarded=False):
    msg = email.message_from_file(open( file_obj.name, "r"))
    original_date = email.utils.parsedate(msg.get("Date"))
    if forwarded:
        try:
            tmp = extract_forwarded_email(msg)
            msg = tmp
        except Error as error:
            logging.info("not a forwarded email?",error)
    eml = Email(key, msg, original_date)
    try:
        body = [None, None]
        for part in msg.get_payload():
            if part.get_filename():
                eml.attachments.append(part)
            else:
                for subpart in part.walk():
                    subcharset = subpart.get_content_charset() or "utf8"
                    if subpart.get_content_type() == "text/plain":
                        text = subpart.get_payload(decode=True)
                        eml.text = text.decode(subcharset)
                    elif subpart.get_content_type() == "text/html":
                        html = subpart.get_payload(decode=True)
                        eml.html = html.decode(subcharset)
        if eml.html:
            parser = LinkParser()
            parser.feed(eml.html)
            eml.links = parser.links
        if eml.date:
            timestamp = time.mktime(eml.date)
            eml.date = datetime.fromtimestamp(timestamp)
    except Exception as excp:
        eml.errors.append(fmt(excp))
    return eml


class DisneyParser(HTMLParser):
    curr = None
    filename = None
    def handle_starttag(self, tag, attrs):
        if tag == "div":
            for a in attrs:
                if a[0] == "class" and a[1] == "fileNameDisplay":
                    self.curr = a[1]
                    break

    def handle_endtag(self, tag):
        self.curr = None

    def handle_data(self, data):
        if self.curr is not None:
            self.filename = data

def extract_disney(eml, dest_dir):
    link = next((l[1] for l in eml.links if l[0] == "Click Here to Download Your File"), None)
    if not link:
        raise Error("disney email: could not find download link")
    page = requests.get(link).content
    parser = LinkParser()
    parser.feed(page)
    link = next((l[1] for l in parser.links if l[0] == "download"), None)
    if not link:
        raise Error("disney email: could not find download link on webpage")
    parser = DisneyParser()
    parser.feed(page)
    if not parser.filename:
        raise Error("disney email: could not find filename")
    link = "https://www.relayit.net/" + link
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36"}
    response = requests.get(link, headers=headers, stream=True)
    dest_file = os.path.join(dest_dir, parser.filename)
    with open(parser.filename, "wb") as f:
        for chunk in response.iter_content(chunk_size=4096):
            if chunk:
                f.write(chunk)
    return dest_file


class EmailProcessor(object):
    """
    EmailProcessor extract attachments from emails in an s3 bucket
    """

    def __init__(self, rules_file, s3_base_url=None, s3_atch_dir=None, aws_access_key_id=None, aws_secret_access_key=None):
        with open(rules_file, "rb") as file_handle:
            self.rules = json.loads(file_handle.read().decode("utf-8"))
        # '__rootdir__' is the root directory in s3 we expect to find the email
        # files. save it to the object, then delete it from the rules (since
        # it's not actually a rule)
        if "__rootdir__" in self.rules:
            del self.rules["__rootdir__"]
        for dest in self.rules:
            rule_sets = to_list(self.rules[dest])
            for rule_set in rule_sets:
                for key in rule_set:
                    rule_set[key] = to_list(rule_set[key])
            self.rules[dest] = rule_sets
        self.client = None
        if not s3_base_url:
            return

        # split the 's3_base_url' into the bucket / directory format that the
        # boto library expects.
        s3_base_url = s3_base_url.strip("/ ")
        if s3_base_url.startswith("s3://"):
            s3_base_url = s3_base_url[5:]
        parts = s3_base_url.split("/")
        self.s3_bucket = parts[0]
        self.s3_base_dir = "/".join(parts[1:])
        self.attachment_dest_dir = self.s3_base_dir + "/" + s3_atch_dir
        #logging.info("email processor", self.s3_bucket, self.s3_base_dir, self.attachment_dest_dir)
        self.client = s3.Client(key=aws_access_key_id, secret=aws_secret_access_key)

    def check_mail(self, update=False):
        """
        checks a given s3 location for new emails
        """
        return self.check_mail_dir(update=update)

    def check_mail_dir(self, directory="", update=False):
        """
        checks a given s3 location for new emails
        """
        directory = (self.s3_base_dir + "/" + directory.strip("/")).strip("/")
        objects = self.client.list_objects(self.s3_bucket, directory)
        results = []
        for obj in objects:
            tmp = tempfile.NamedTemporaryFile(mode='w',delete=False)
            tmp.close()
            with open(tmp.name, "wb") as file_handle:
                self.client.get_object(self.s3_bucket, obj["Key"], file_handle)
            eml = self.check_object(tmp, obj["Key"], update)
            if eml:
                #logging.info(eml)
                #logging.info(50*"-")
                results.append(eml)
            tmp.close()
            #os.remove(tmp.name)
        return results

    def check_object(self, file_obj, key, update=False):
        """
        download a file from s3 as a in-memory object and attempts to parse it
        as an email / extract possible attachments
        """
        #logging.info(" ==> checking email:", key)
        try:
            eml = parse_email(key, file_obj, forwarded=True)
        except Exception as excp:
            eml = Email(key)
            eml.errors.append(fmt(excp))
            return eml
        try:
            # edge cases
            destinations = email_destinations(eml, self.rules)
            is_local = False
            if not eml.errors and update and self.client:
                destination_dir = os.path.join(self.attachment_dest_dir, destinations[0])
                self.place_attachments(eml, destination_dir, is_local)
                self.move_email(key, "Processed", eml.date)
        except Error as error:
            eml.errors.append(fmt(error))
        except Exception as excp:
            eml.errors.append(fmt(excp))
        return eml

    def place_attachments(self, eml, destination_dir, attachment_is_local=False):
        for attachment in eml.attachments:
            timestamp = eml.date.strftime("%Y%m%d_%H%M%S_")
            if attachment_is_local:
                filename = os.path.basename(attachment)
                data = open(attachment, "rb")
            else:
                filename = get_attachment_name(attachment)
                data = io.BytesIO(attachment.get_payload(decode=True))
            ext = os.path.splitext(filename)[1].lower()
            # check for zip file. we extract zip file members as part of the
            # email processing so the audit  file configuration can target
            # specific / multiple files.
            if ext == ".zip":
                #logging.info("opening zip archive", filename)
                zipf = zipfile.ZipFile(data, "r")
                for member in zipf.namelist():
                    dest_key = os.path.join(destination_dir, timestamp + os.path.basename(member))
                    dest_key = dest_key.replace('\\','/')
                    #logging.info("extracting zip file", member, "to", dest_key)
                    data = zipf.open(member, "r").read()
                    self.client.put_object(data, self.s3_bucket, dest_key)
            else:
                dest_key = os.path.join(destination_dir, timestamp + filename)
                dest_key = dest_key.replace('\\','/')
                #print(self.s3_bucket, dest_key)
                #logging.info("extracting attachment", filename, "to", dest_key)
                self.client.put_object(data, self.s3_bucket, dest_key)

    def move_email(self, s3key, directory, date):
        """
        move the original s3 file to a final location to prevent re-processing
        it
        """
        dest_key = os.path.join(self.s3_base_dir, directory)
        
        if date is not None:
            dest_key = os.path.join(dest_key, date.strftime("%Y%m%d"), os.path.basename(s3key))
        else:
            dest_key = os.path.join(dest_key, os.path.basename(s3key))
        if dest_key == s3key:
            return
        dest_key = dest_key.replace('\\','/')
        #logging.info("moving file", repr(s3key), "->", repr(dest_key))
        self.client.copy_object(self.s3_bucket, s3key, self.s3_bucket, dest_key)
        self.client.delete_object(self.s3_bucket, s3key)


def get_attachment_name(attachment):
    name = attachment
    if not isinstance(name, str):
        name = attachment.get_filename()
    return decode_email_header(name)


def email_destinations(message, rules):
    """
    returns the email rules that match this message.
    """
    matching = set()
    for dest in rules:
        if email_matches_rule(message, rules[dest]):
            matching.add(dest)
    return list(matching)

def email_matches_rule(eml, rule_sets):
    def val(eml, key):
        if key == "From":
            return eml.fr.lower()
        elif key == "Subject":
            return eml.subject.lower()
        elif key == "Body":
            return eml.text.lower() + " " + eml.html.lower()
        return ""
    for rule_set in rule_sets:
        okay = True
        for key in rule_set:
            options = rule_set[key]
            if not any([o.lower() in val(eml, key) for o in options]):
                # the key (and rule_set) are not a match
                okay = False
                break
        if okay:
            return True
    return False

# vim: set sw=4 sts=4 ts=4 et:
