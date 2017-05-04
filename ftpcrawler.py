import re
import io
from ftplib import FTP
from datetime import datetime
from filecrawler import FileCrawler
from model import AmbarCrawlerSettings, AmbarCrawlerSettingsCredentials, AmbarFileMeta
from logger import AmbarLogger

class FtpEntry(object):
    def __init__(self):
        self.fullName = ''
        self.shortName = ''
        self.updatedDatetime = None
        self.size = 0
        self.isDirectory = None
    
    @classmethod
    def Init(cls, LocationPath, EntryLine):
        entry = cls()
        entryPars = re.split('[\s]+', EntryLine)            
        if len(entryPars) != 9:
            return None            
        if entryPars[0].strip()[0:1] == 'd':
            entry.isDirectory = True
        else:
            entry.isDirectory = False            
        if not entry.isDirectory:
            entry.size = int(entryPars[4])
        entry.shortName = entryPars[8].strip()
        entry.fullName = re.sub('[\/]+','/','{0}/{1}'.format(LocationPath, entry.shortName))
        updatedDatetimeString = '{0} {1} {2}'.format(entryPars[5],entryPars[6],entryPars[7])        
        try:
            entry.updatedDatetime = datetime.strptime('{0} {1}'.format(datetime.now().year, updatedDatetimeString), '%Y %b %d %H:%M').replace(hour=0, minute=0)
        except:
            pass        
        if not entry.updatedDatetime:
            try:
                entry.updatedDatetime = datetime.strptime(updatedDatetimeString, '%b %d %Y')
            except:
                pass
        return entry              

class FtpProxy(object):
    def __init__(self):   
        self.connection = None     
        self.username = ''
        self.password = ''
        self.serverName = ''
        self.serverIp = ''
        self.isConnected = False
        self.logger = None

    @classmethod
    def Init(cls, ServerName, ServerIp, UserName, Password, Logger):
        ftpProxy = cls()
        ## initializing logger
        ftpProxy.logger = Logger
        ## initializing...
        ftpProxy.username = str(UserName)
        if ftpProxy.username == '':
            ftpProxy.username = 'anonymous'
        ftpProxy.password = str(Password)
        ftpProxy.serverName = str(ServerName)
        ftpProxy.serverIp = str(ServerIp)
        ftpProxy.isConnected = False     
        return ftpProxy

    def connectByServerName(self):
        try:
            self.connection = FTP(self.serverName)
            self.connection.login(user = self.username, passwd = self.password)
            self.isConnected = True
            return self.isConnected
        except Exception as e:
            self.logger.LogMessage('error', str(e))
            return False
    
    def connectByServerIp(self):
        try:
            self.connection = FTP(self.serverIp)
            self.connection.login(user = self.username, passwd = self.password)
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
    
    def parseLocationEntry(self, locationPath, entry, entries):
        ftpEntry = None

        try:
            ftpEntry = FtpEntry.Init(locationPath, entry)
        except Exception as e:
            self.logger.LogMessage('error', 'error parsing entry {0} in {1} {2}'.format(entry, locationPath, str(e)))
       
        if ftpEntry:
            entries.append(ftpEntry)

    def ListLocation(self, LocationPath):
        if not self.isConnected:
            return None
        
        if len(LocationPath) == 0:
            LocationPath = '/'
        if LocationPath[0:1] != '/':
            LocationPath = '/{0}'.format(LocationPath)
        LocationPath = re.sub('[\/]+', '/', LocationPath)

        try:
            entries = []
            self.connection.retrlines('LIST {0}'.format(LocationPath), lambda entry: self.parseLocationEntry(LocationPath, entry, entries))
            return entries
        except Exception as e:
            self.logger.LogMessage('error', 'error listing {0} {1}'.format(LocationPath, str(e)))
            return None

    def RetrieveFile(self, FullFileName):
        if not self.isConnected:
            return None

        try:
            fileStream = io.BytesIO()
            self.connection.retrbinary('RETR {0}'.format(FullFileName), fileStream.write, blocksize=1024)
            return fileStream
        except Exception as e:
            self.logger.LogMessage('info', 'could not retrieve file {0} {1}'.format(FullFileName, str(e)))
            return None    

class FtpCrawler(FileCrawler):      
    ## __init__() inherited from FileCrawler

    ## inherited method Crawl
    def Crawl(self):
        """Crawling folders from AmbarCrawlerSettings recursively
        """
        for location in self.settings.locations:  

            ftpProxy = FtpProxy.Init(location.host_name, location.ip_address, self.settings.credentials.login, self.settings.credentials.password, self.logger)

            if not ftpProxy:
                self.logger.LogMessage('error', 'error initializing FtpProxy for {0}'.format(location.host_name))
                return

            if not ftpProxy.Connect():
                self.logger.LogMessage('error', 'error connecting to Ftp server on {0}'.format(location.host_name))
                return

            self.logger.LogMessage('info', 'crawling {1} at {0}'.format(location.host_name, location.location))

            self.CrawlFtpSubFoldersRecursive(ftpProxy, location.location)     
        
        self.logger.LogMessage('info', 'done')
    
    ## inner crawling recursively method
    def CrawlFtpSubFoldersRecursive(self, ftpProxy, currentLocation):
        """Private method, nevermind
        """
        pathListed = ftpProxy.ListLocation(currentLocation)

        if not pathListed:
            return

        for ftpEntry in pathListed:
            if ftpEntry.isDirectory:
                self.CrawlFtpSubFoldersRecursive(ftpProxy, ftpEntry.fullName)
                continue
            
            size = ftpEntry.size
            fullName = '//{0}'.format(re.sub('[\/]+','/','{0}/{1}'.format(ftpProxy.serverName, ftpEntry.fullName).lower()))
            shortName = ftpEntry.shortName.lower() 
            createTime = ftpEntry.updatedDatetime
            updateTime = ftpEntry.updatedDatetime

            if not self.regex.search(shortName):
                self.logger.LogMessage('verbose','ignoring {0}'.format(fullName))
                continue

            if ftpEntry.size > self.settings.max_file_size_bytes:
                self.logger.LogMessage('verbose','ignoring too big {0}'.format(fullName))   
                continue

            if self.TurboCheckMetaExistanceCallback(createTime, updateTime, shortName, fullName):
                self.logger.LogMessage('verbose','[TURBO] meta found {0}'.format(fullName))
                continue

            fileData = ftpProxy.RetrieveFile(ftpEntry.fullName)

            if fileData:                    
                self.ProcessFileCallback(fileData, size, createTime, updateTime, shortName, fullName)