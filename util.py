from __future__ import absolute_import
from __future__ import print_function

import errno
import os
import subprocess


class Error(Exception):
    """
    error is a class for application level exceptions.
    """
    def __init__(self, *args, **kwargs):
        super(Error, self).__init__(fmt(*args, **kwargs))

def fmt(*args, **kwargs):
    """
    all non-keyword args are concatenated using spaces. if there are any
    keyword args, they are appended in "key=value" form and joined with a comma

    for example:
        details = "error details"
        print fmtmsg("an error occured:", details, foo=1, bar=False)
    will print:
        an error occured: error details (foo=1, bar=False)
    """
    msg = " ".join([a for a in args])
    if kwargs:
        kvs = ["{}={}".format(to_s(k), to_s(kwargs[k])) for k in kwargs]
        msg += " ({})".format(", ".join(kvs))
    return msg


def strip_newlines(text):
    return (text or "").replace("\r\n", " ").replace("\n", " ")


def to_s(arg):
    """
    helper function to convert values to a string object
    """
    str(arg)


def to_f(arg):
    """
    helper function used in metric sum calculations. if the string value is
    not a valid float, just return 0.0
    """
    try:
        return float(arg)
    except ValueError as _:
        return 0.0


def mkdirp(dirpath):
    """
    XXX raise error is path exists but is a file?
    """
    if os.path.exists(dirpath):
        return
    try:
        os.makedirs(dirpath)
    except OSError as exc:
        if exc.errno != errno.EEXIST:
            raise


def unquote(string):
    """
    remove quotes from a string (single or double) if they exist
    """
    if len(string) < 3 or string[0] != string[-1]:
        return string
    if string[0] in  ['"', "'"]:
        return string[1:-1]
    return string


def to_list(obj):
    if not isinstance(obj, list):
        obj = [obj]
    return obj


def devmode():
    return os.environ.get("FRP_ENV", "") == "dev"


def env_id_to_password(env_id):
    """
    uses the `fun_set_pass_key_from_file_to_var` bash function to retrieve and
    decrypt secrets
    """
    cmd = "source $RESOURCE_DIR/Scripts/ENV/.env_file.lib"
    cmd += " && fun_set_pass_key_from_file_to_var " + str(env_id)
    return subprocess.check_output(["bash", "-c", cmd]).rstrip()



# vim: set sw=4 sts=4 ts=4 et:
