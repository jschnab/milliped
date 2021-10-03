import errno
import hashlib
import logging
import os
import signal

from collections import deque
from functools import wraps
from urllib.error import URLError
from urllib.parse import urljoin
from urllib.robotparser import RobotFileParser

import boto3


def check_status(response):
    """
    Check that HTTP status code of the response from a call to AWS is 200.

    :param dict response: response to the AWS call
    :raises ValueError: if response HTTP status code is not 200
    """
    code = response.get("ResponseMetadata", {}).get("HTTPStatusCode", 0)
    if code != 200:
        raise ValueError(f"Expected HTTP status code 200, got: {code}")


def cut_url(url):
    """
    If URL is longer than 50 characters, show the last 45.
    Useful for logging.

    :param str url:
    :return str: short URL
    """
    if len(url) > 50:
        return f"...{url[-45:]}"
    return url


class LocalExploredSet:
    """
    Class that stores explored web pages contents implemented using the Python
    built-in 'set' object.
    """
    def __init__(self):
        self.explored = set()

    def __len__(self):
        return len(self.explored)

    def __repr__(self):
        return repr(self.explored)

    def __contains__(self, item):
        return item in self.explored

    def add(self, *args):
        """
        Add args to the set.
        Note: args should be of type 'string'.
        """
        for a in args:
            if not isinstance(a, str):
                raise TypeError(f"Expected {a} to be str, got {type(a)}")
            self.explored.add(hashlib.md5(a.encode()).hexdigest())

    def clear(self):
        """
        Delete all items from the set.
        """
        self.explored.clear()


class LocalQueue:
    """
    In-memory queue implemented using the Python class collections.deque.
    """
    def __init__(self):
        self.queue = deque()

    def enqueue(self, item):
        self.queue.appendleft(item)

    def dequeue(self):
        return self.queue.pop()

    def __len__(self):
        return len(self.queue)

    @property
    def is_empty(self):
        return len(self.queue) == 0


class RobotParser:
    def __init__(self, base_url, user_agent=None):
        self.base_url = base_url
        self.user_agent = user_agent or "*"
        self.parser = RobotFileParser()
        self.parser.set_url(urljoin(base_url, "robots.txt"))
        try:
            self.parser.read()
            if self.parser.crawl_delay(self.user_agent):
                self.request_delay = self.parser.crawl_delay(self.user_agent)
            else:
                self.request_delay = None
        except URLError:
            logging.warning(
                "could not find robots.txt, setting no request delay."
            )
            self.request_delay = 0
            self.parser = None

    def can_fetch(self, url):
        """
        Checks the robots.txt file if we can fetch the page.
        Always returns True if the website does not have a robots.txt file.

        :param str url: url to check
        :return bool: True if we can browse the page else False
        """
        if not url.startswith(self.base_url):
            url = urljoin(self.base_url, url)
        if self.parser:
            return self.parser.can_fetch(self.user_agent, url)
        return False


class SQSQueue:
    def __init__(self, queue_url, wait_seconds=20):
        self.queue_url = queue_url
        self.wait_seconds = wait_seconds
        self.client = boto3.client("sqs")

    def enqueue(self, item):
        """
        Enqueue item into an SQS queue.

        :param str item: item to push to add to the queue
        """
        response = self.client.send_message(
            QueueUrl=self.queue_url,
            MessageBody=item,
        )
        check_status(response)

    def dequeue(self):
        """
        Dequeue item from an SQS queue.

        :return str: message body of an item from the queue
        """
        response = self.client.receive_message(
            QueueUrl=self.queue_url,
            WaitTimeSeconds=self.wait_seconds
        )
        check_status(response)
        messages = response.get("Messages")
        if messages:
            # we only receive one message at a time
            handle = messages[0].get("ReceiptHandle")
            body = messages[0].get("Body")
            self.client.delete_message(
                QueueUrl=self.queue_url,
                ReceiptHandle=handle,
            )
            return body

    def __len__(self):
        resp = self.client.get_queue_attributes(
            QueueUrl=self.queue_url,
            AttributeNames=["ApproximateNumberOfMessages"]
        )
        check_status(resp)
        n = resp.get("Attributes", {}).get("ApproximateNumberOfMessages", 0)
        return int(n)

    @property
    def is_empty(self):
        return len(self) == 0


class TimeoutError(Exception):
    pass


def timeout(seconds=10, error_message=os.strerror(errno.ETIME)):
    def decorator(func):
        def handle_timeout(signum, frame):
            raise TimeoutError(error_message)

        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, handle_timeout)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result

        return wraps(func)(wrapper)

    return decorator
