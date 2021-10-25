from collections import deque

import boto3
import botocore

import milliped.constants as cst

from milliped.utils import check_status, get_logger

LOGGER = get_logger(__name__)


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

        :param args: Strings to add to the set.
        """
        for a in args:
            self.explored.add(a)

    def clear(self):
        """
        Delete all items from the set.
        """
        self.explored.clear()


class LocalQueue:
    """
    In-memory queue implemented using the Python class collections.deque.

    The "enqueue" method adds an item to the queue. The "dequeue" method
    returns an item from the queue.

    The "enqueue" method does not enqueue an item that was enqueued previously,
    because it keeps items in a hash set. Thus this class can only process
    items that are hashable.

    To re-enqueue an item, once should use the "re_enqueue" method.
    """

    def __init__(self, name=cst.QUEUE_NAME, logger=LOGGER):
        self.name = name
        self.queue = deque()
        self.seen_items = set()
        self.logger = logger

    def __len__(self):
        return len(self.queue)

    def __contains__(self, item):
        return item in self.seen_items

    def enqueue(self, item):
        """
        Add an item to the queue.

        :param str item: Item to add to the queue.
        """
        if item not in self.seen_items:
            self.logger.info(f"Enqueue to {self.name}: {item}")
            self.seen_items.add(item)
            self.queue.appendleft(item)

    def re_enqueue(self, item):
        """
        Add an item to the queue, even if this item was previously added. This
        is useful to process items more than once.

        :param str item: Item to add to the queue.
        """
        self.logger.info(f"Enqueue to {self.name}: {item}")
        self.queue.appendleft(item)

    def dequeue(self):
        """
        Dequeue an item and return it.

        :returns (str): Item from the queue.
        """
        item = self.queue.pop()
        self.logger.info(f"Dequeue from {self.name}: {item}")
        return item

    @property
    def is_empty(self):
        return len(self.queue) == 0


class SQSQueue:
    """
    In-memory queue implemented using AWS SQS and DynamoDB to avoiding storing
    duplicate items.

    The "enqueue" method adds an item to the queue. The "dequeue" method
    returns an item from the queue.

    The "enqueue" method does not enqueue an item that was enqueued previously,
    because it keeps items in a hash set. Thus this class can only process
    items that are hashable.

    To re-enqueue an item, once should use the "re_enqueue" method.

    The following AWS resources must be configured before instantiating this
    class:
    - an AWS standard queue
    - a DynamoDB table with a partition key of type string and name "id"
    - permissions to send message, receive message and get queue attributes
      from the relevant SQS queue, as well as put an item into the relevant
      DynamoDB table
    - the environment variables AWS_PROFILE and AWS_REGION to assume AWS
      permissions

    :param str queue_url: URL of the SQS queue.
    :param str dynamo_table: Name of the DynamoDB table.
    :param int wait_seconds: Number of seconds to use for long polling of the
        SQS queue.
    :param logging.Logger logger: Configured logger object.
    """

    def __init__(
        self, queue_url, dynamo_table, wait_seconds=20, logger=LOGGER
    ):
        self.queue_url = queue_url
        self.name = self.queue_url.split("/")[-1]
        self.dynamo_table = dynamo_table
        self.wait_seconds = wait_seconds
        self.logger = logger
        self.sqs_client = boto3.client("sqs")
        self.dynamo_client = boto3.client("dynamodb")
        logger.info(f"SQS queue '{self.name}' ready")

    def __len__(self):
        n = 0
        # SQS is highly distributed and only gives an approximate number of
        # messages remaining in the queue, so we repeat the API call
        for _ in range(3):
            resp = self.sqs_client.get_queue_attributes(
                QueueUrl=self.queue_url,
                AttributeNames=["ApproximateNumberOfMessages"],
            )
            check_status(resp)
            n = max(
                n,
                int(
                    resp.get("Attributes", {}).get(
                        "ApproximateNumberOfMessages", 0
                    )
                ),
            )
        return n

    def __contains__(self, item):
        try:
            response = self.dynamo_client.put_item(
                TableName=self.dynamo_table,
                Item={"id": {"S": item}},
                ConditionExpression="attribute_not_exists(#id)",
                ExpressionAttributeNames={"#id": "id"},
            )
            check_status(response)
        except botocore.exceptions.ClientError as e:
            if (
                e.response["Error"]["Code"]
                == "ConditionalCheckFailedException"
            ):
                return True
            else:
                raise
        return False

    def enqueue(self, item):
        """
        Enqueue item into an SQS queue.

        :param str item: Item to push to add to the queue.
        """
        if item not in self:
            self.logger.info(f"Enqueue to {self.name}: {item}")
            response = self.sqs_client.send_message(
                QueueUrl=self.queue_url, MessageBody=item,
            )
            check_status(response)

    def re_enqueue(self, item):
        """
        Add an item to an SQS queue, even if this item was previously added.
        This is useful to process items more than once.

        :param str item: Item to add to the queue.
        """
        self.logger.info(f"Enqueue to {self.name}: {item}")
        response = self.sqs_client.send_message(
            QueueUrl=self.queue_url, MessageBody=item,
        )
        check_status(response)

    def dequeue(self):
        """
        Dequeue item from an SQS queue.

        :returns (str): Message body of an item from the queue.
        """
        self.logger.info(f"Polling {self.harvest}")
        response = self.sqs_client.receive_message(
            QueueUrl=self.queue_url, WaitTimeSeconds=self.wait_seconds
        )
        check_status(response)
        messages = response.get("Messages")
        if messages:
            # we only receive one message at a time
            handle = messages[0].get("ReceiptHandle")
            body = messages[0].get("Body")
            self.sqs_client.delete_message(
                QueueUrl=self.queue_url, ReceiptHandle=handle,
            )
            self.logger.info(f"Dequeue from {self.name}: {body}")
            return body

    @property
    def is_empty(self):
        return len(self) == 0
