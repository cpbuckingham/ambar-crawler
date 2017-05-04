from apiproxy import ApiProxy
from model import AmbarCrawlerSettings
from smbcrawler import SmbCrawler
from dropboxcrawler import DropboxCrawler
from ftpcrawler import FtpCrawler
from imapcrawler import ImapCrawler
from logger import AmbarLogger
import json
import signal
import pika
import sys
import re
import argparse
import gc

RABBIT_QUEUE_NAME = 'AMBAR_CRAWLER_QUEUE'

parser = argparse.ArgumentParser()
parser.add_argument('-api_url', default='http://localhost:8080')
parser.add_argument('-rabbit_host', default='amqp://ambar')
parser.add_argument('-rabbit_heartbeat', default=0)
parser.add_argument('-api_call_timeout_seconds', default=1200)
parser.add_argument('-name', default='c0')
parser.add_argument('-api_token', default='')

args = parser.parse_args()

## instantiating api proxy
apiProxy = ApiProxy(args.name, args.api_url, args.api_call_timeout_seconds, args.api_token)

## connecting to Rabbit
coreLogger = AmbarLogger(apiProxy, args.name, True)
coreLogger.LogMessage('info', 'connecting to Rabbit {0}...'.format(args.rabbit_host))
try:
    rabbitConnection = pika.BlockingConnection(pika.URLParameters('{0}?heartbeat={1}'.format(args.rabbit_host, args.rabbit_heartbeat)))
    rabbitChannel = rabbitConnection.channel()
    rabbitChannel.basic_qos(prefetch_count=1)
    coreLogger.LogMessage('info', 'connected to Rabbit!')
    coreLogger.LogMessage('info','waiting for messages...')
except Exception as e:
    coreLogger.LogMessage('error', 'error initializing connection to Rabbit {0}'.format(repr(e)))
    exit(1)     

def PerformTask(CrawlerUid):    
    ## loading crawler settings
    apiResp = apiProxy.GetAmbarCrawlerSettings(CrawlerUid)   

    if not apiResp.Success: 
        coreLogger.LogMessage('error', 'error loading crawler settings for uid {0} {1}'.format(CrawlerUid, apiResp.message))
        return False

    if not apiResp.Ok:
        coreLogger.LogMessage('error', 'error loading crawler settings for uid {0} {1}'.format(CrawlerUid, apiResp.message))
        return False

    ## initializing settings for the task
    try:
        ambarCrawlerSettings = AmbarCrawlerSettings.Init(apiResp.payload)
    except Exception as ex:
        coreLogger.LogMessage('error', 'error initializing crawler setup for uid {0}, error message: {1}'.format(CrawlerUid, str(ex)))
        return False

    ## checking crawler type
    if not (ambarCrawlerSettings.type == 'smb' or ambarCrawlerSettings.type == 'dropbox' or ambarCrawlerSettings.type == 'ftp' or ambarCrawlerSettings.type == 'imap'):
        coreLogger.LogMessage('error', 'unknown crawler type {0}'.format(ambarCrawlerSettings.type))
        return False
    
    ## start
    coreLogger.LogMessage('info','starting task uid {0}'.format(ambarCrawlerSettings.uid))

    ## reporting started
    apiResp = apiProxy.ReportStarted(ambarCrawlerSettings.uid)

    if not apiResp.Success: 
        coreLogger.LogMessage('error', 'error reporting start for task with uid {0} {1}'.format(ambarCrawlerSettings.uid, apiResp.message))
        return False    
    
    if apiResp.Conflict:
        coreLogger.LogMessage('info', 'task with uid {0} is already being executed, ignoring...'.format(ambarCrawlerSettings.uid))
        return False
    
    if not apiResp.Ok: 
        coreLogger.LogMessage('error', 'error reporting start for task with uid {0} {1} {2}'.format(ambarCrawlerSettings.uid, apiResp.code, apiResp.message))
        return False 

    ## init
    coreLogger.LogMessage('info','settings for uid {0} intialized'.format(ambarCrawlerSettings.uid))

    ## crawling    
    if ambarCrawlerSettings.type == 'smb':
        crawler = SmbCrawler(apiProxy, ambarCrawlerSettings)
    if ambarCrawlerSettings.type == 'dropbox': 
        crawler = DropboxCrawler(apiProxy, ambarCrawlerSettings)
    if ambarCrawlerSettings.type == 'ftp': 
        crawler = FtpCrawler(apiProxy, ambarCrawlerSettings)
    if ambarCrawlerSettings.type == 'imap': 
        crawler = ImapCrawler(apiProxy, ambarCrawlerSettings)

    try:
        crawler.Crawl()
    except Exception as ex:
        coreLogger.LogMessage('info','task with uid {0} exited with error {1}'.format(ambarCrawlerSettings.uid, str(ex)))
    
    ## finish
    coreLogger.LogMessage('info','task uid {0} finished'.format(ambarCrawlerSettings.uid))

    ## reporting finished
    apiResp = apiProxy.ReportFinished()

    if not apiResp.Ok: 
        coreLogger.LogMessage('error', 'error reporting finish for task with uid {0} {1}'.format(ambarCrawlerSettings.uid, apiResp.message))
        return False    
    
    coreLogger.LogMessage('info', 'task with uid {0} completed'.format(ambarCrawlerSettings.uid))
    return True

def RabbitConsumeCallback(channel, method, properties, body):
    try:
        crawlerUid = json.loads(body.decode('utf-8'))['uid']
    except Exception as ex:
        channel.basic_nack(delivery_tag = method.delivery_tag, requeue=False)
        coreLogger.LogMessage('error', 'wrong task format')
        return

    coreLogger.LogMessage('info', 'task received for uid {0}'.format(crawlerUid))    

    PerformTask(crawlerUid)

    gc.collect()

rabbitChannel.basic_consume(RabbitConsumeCallback, queue=RABBIT_QUEUE_NAME, no_ack=True)
rabbitChannel.start_consuming()

exit(0)