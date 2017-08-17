import imaplib
import email
import email.generator
import os
import re
import io
from datetime import datetime
from time import mktime
from filecrawler import FileCrawler
from model import AmbarCrawlerSettings, AmbarCrawlerSettingsCredentials, AmbarFileMeta
from logger import AmbarLogger

class ImapProxy(object):
    def __init__(self):
        self.connection = None     
        self.username = ''
        self.password = ''
        self.email = ''
        self.serverName = ''
        self.serverIp = ''
        self.isConnected = False
        self.logger = None

    @classmethod
    def Init(cls, ServerName, ServerIp, UserName, Password, Email, Logger):
        imapProxy = cls()
        ## initializing logger
        imapProxy.logger = Logger
        ## initializing...
        imapProxy.username = str(UserName)
        imapProxy.password = str(Password)
        imapProxy.serverName = str(ServerName)
        imapProxy.serverIp = str(ServerIp)
        imapProxy.isConnected = False     
        imapProxy.email = Email
        return imapProxy

    def connectByServerName(self):
        try:
            self.connection = imaplib.IMAP4_SSL(self.serverName)
            self.connection.login(self.username, self.password)
            self.connection.select()
            self.isConnected = True
            return self.isConnected
        except Exception as e:
            self.logger.LogMessage('error', str(e))
            return False
    
    def connectByServerIp(self):
        try:
            self.connection = imaplib.IMAP4_SSL(self.serverIp)
            self.connection.login(self.username, self.password)
            self.connection.select()
            self.isConnected = True
            return self.isConnected
        except Exception as e:
            self.logger.LogMessage('error', str(e))
            return False

    def Connect(self):
        if self.connectByServerName():
            return True

        if self.connectByServerIp():
            return True

        return False
    
    def Disconnect(self):
        try:
            self.connection.close()
            self.connection.logout()
        except:
            pass

    def normalizeFileName(self, fileName):
        return "".join([str(c) for c in fileName if str(c).isalpha() or str(c).isdigit() or str(c)==' ']).rstrip()

    def decodeStringFromMail(self, string):
        try:
            header, encoding = email.header.decode_header(string)[0]          
            if not encoding:
                return header
            if encoding == 'unknown-8bit':
                return None

            return header.decode(encoding)
        except Exception as e:
            self.logger.LogMessage('info', 'can not decode string {0}'.format(str(e)))
            return None

    def processMessage(self, messageId, ProcessMessageCallback):
        try:
            callResult, data = self.connection.uid('fetch', messageId, '(BODY.PEEK[])')

            if callResult != 'OK' or not data[0]:
                raise Exception('failed to fetch')

            rawEmail = data[0][1]
            emailMessage = email.message_from_bytes(rawEmail)
            
            shortName = self.decodeStringFromMail(emailMessage.get('Subject'))
            shortName = self.normalizeFileName(shortName if shortName else str(messageId))
            shortName = '{0}.eml'.format(shortName)
            fullName = '//{0}/{1}/{2}'.format(self.serverName, self.email, shortName).lower()
            createUpdateTime = datetime.fromtimestamp(mktime(email.utils.parsedate(emailMessage.get('Date'))))

            ProcessMessageCallback(shortName, fullName, createUpdateTime, rawEmail)

            if emailMessage.get_content_maintype() != 'multipart':
                return

            for part in emailMessage.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                if part.get('Content-Disposition') is None:
                    continue
            
                partFilename = part.get_filename()

                if not partFilename:
                    continue

                partFilename = self.decodeStringFromMail(partFilename).lower()

                partData = part.get_payload(decode=True)
                
                if not partData:
                    continue                
               
                fullPartFileName = '{0}/{1}'.format(fullName, partFilename).lower()

                ProcessMessageCallback(partFilename, fullPartFileName, createUpdateTime, partData)

        except Exception as e:
            self.logger.LogMessage('error', 'error retrieving message {0} {1}'.format(messageId, str(e)))
            return None

    def ListMailBox(self, ProcessMessageCallback):
        try:
            callResult, rawUidList = self.connection.uid('search', None, "ALL") 
            
            if callResult != 'OK':
                self.logger.LogMessage('error', 'error listing mailbox {0}'.format(callResult))
                return
            
            if not rawUidList:
                self.logger.LogMessage('error', 'error listing mailbox empty response received')
                return

            uidList = reversed(rawUidList[0].split())

            for messageId in uidList:   
                self.processMessage(messageId, ProcessMessageCallback)

        except Exception as e:
            self.logger.LogMessage('error', 'error listing mailbox {0}'.format(str(e)))
            return None


class ImapCrawler(FileCrawler):      
    ## __init__() inherited from FileCrawler

    ## inherited method Crawl
    def Crawl(self):
        """Crawling folders from AmbarCrawlerSettings recursively
        """
        for location in self.settings.locations:            
            imapProxy = ImapProxy.Init(location.host_name, location.ip_address, self.settings.credentials.login, self.settings.credentials.password, location.location, self.logger)

            if not imapProxy:
                self.logger.LogMessage('error', 'error initializing ImapProxy for {0}'.format(location.host_name))
                return

            if not imapProxy.Connect():
                self.logger.LogMessage('error', 'error connecting to Imap server on {0}'.format(location.host_name))
                return

            self.logger.LogMessage('info', 'crawling {1} at {0}'.format(location.host_name, location.location))

            imapProxy.ListMailBox(self.ProcessMessageCallback)   
            
            imapProxy.Disconnect()

        self.logger.LogMessage('info', 'done')
    
    def ProcessMessageCallback(self, ShortName, FullName, CreateUpdateTime, FileData):
        if not self.regex.search(ShortName):
            self.logger.LogMessage('verbose','ignoring {0}'.format(FullName))
            return

        if len(FileData) > self.settings.max_file_size_bytes:
            self.logger.LogMessage('verbose','ignoring too big {0}'.format(FullName))   
            return

        if self.TurboCheckMetaExistanceCallback(CreateUpdateTime, CreateUpdateTime, ShortName, FullName):
            self.logger.LogMessage('verbose','[TURBO] meta found {0}'.format(FullName))
            return
                   
        self.ProcessFileCallback(io.BytesIO(FileData), len(FileData), CreateUpdateTime, CreateUpdateTime, ShortName, FullName)

            








