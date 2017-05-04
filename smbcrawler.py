import re
import io
import tempfile
from datetime import datetime
from smb.SMBConnection import SMBConnection
from filecrawler import FileCrawler
import socket
from model import AmbarCrawlerSettings, AmbarCrawlerSettingsCredentials, AmbarFileMeta
from logger import AmbarLogger

class SmbProxy(object):
    def __init__(self):        
        self.domain    = ''
        self.username  = ''
        self.password  = ''
        self.client    = ''
        self.server    = ''
        self.server_ip = ''
        self.share     = ''
        self.port      = ''
        self.conn      = ''
        self.connected = False
        self.settings  = None
        self.logger    = None
        self.callTimeout = 120

    @classmethod
    def Init(cls, Location, Share, CrawlerSettings, Logger, Port=139, CallTimeout=120):
        smbProxy = cls()
        domain, username = CrawlerSettings.credentials.login.split('\\') if CrawlerSettings.credentials.login.count('\\') == 1 else ('', CrawlerSettings.credentials.login)
        ## initializing settings and logger
        smbProxy.settings  = CrawlerSettings
        smbProxy.logger = Logger
        ## initializing...
        smbProxy.domain    = str(domain)
        smbProxy.username  = str(username)
        smbProxy.password  = str(CrawlerSettings.credentials.password)
        smbProxy.client    = socket.gethostname()
        smbProxy.server    = str(Location.host_name)
        smbProxy.server_ip = str(Location.ip_address)
        smbProxy.share     = str(Share)
        smbProxy.port      = Port
        smbProxy.conn      = None
        smbProxy.connected = False     
        smbProxy.callTimeout = CallTimeout           
        return smbProxy

    def Connect(self):
        try:
            self.conn = SMBConnection(self.username, self.password,
                                      self.client, self.server,
                                      use_ntlm_v2=True, domain=self.domain)
            self.connected = self.conn.connect(self.server_ip, self.port)
            return self.connected
        except Exception as e:
            self.logger.LogMessage('error', str(e))
            return None
    
    def ListLocation(self, Location):
        try:
            return self.conn.listPath(self.share, Location, timeout = self.callTimeout)
        except Exception as e:
            self.logger.LogMessage('error', str(e))
            return None

    def RetrieveFile(self, Location, FileName):
        try:
            fileStream = io.BytesIO()
            self.conn.retrieveFile(self.share, '{0}/{1}'.format(Location,FileName).replace('//','/'), fileStream, timeout = self.callTimeout)
            return fileStream
        except Exception as e:
            self.logger.LogMessage('info', 'could not open file {0}/{1}, message: {2}'.format(Location,FileName,e))
            return None

class SmbCrawler(FileCrawler):      
    ## __init__() inherited from FileCrawler

    ## inherited method Crawl
    def Crawl(self):
        """Crawling folders from AmbarCrawlerSettings recursively
        """
        for location in self.settings.locations:  
            regex = re.compile(r'[^\/]+/',re.I)  

            if regex.match(location.location):        
                share = location.location.partition('/')[0]
                currentLocation = location.location.partition('/')[2]
            else:
                share = location.location
                currentLocation = ''

            smbProxy = SmbProxy.Init(location, share, self.settings, self.logger)

            if not smbProxy:
                self.logger.LogMessage('error', 'error initializing SmbProxy for {0}'.format(location.host_name))
                return

            if not smbProxy.Connect():
                self.logger.LogMessage('error', 'error connecting to Smb share on {0}'.format(location.host_name))
                return

            self.logger.LogMessage('info', 'crawling {0}/{1}/{2}'.format(location.host_name, share, currentLocation))

            self.CrawlSmbSubFoldersRecursive(smbProxy, currentLocation)     
        
        self.logger.LogMessage('info', 'done')
    
    ## inner crawling recursively method
    def CrawlSmbSubFoldersRecursive(self, smbProxy, currentLocation):
        """Private method, nevermind
        """
        pathListed = smbProxy.ListLocation(currentLocation)

        if not pathListed:
            return

        for smbObject in pathListed:
            if smbObject.filename == '.' or  smbObject.filename == '..':
                continue
            
            if smbObject.isDirectory:
                self.CrawlSmbSubFoldersRecursive(smbProxy, '{0}/{1}'.format(currentLocation,smbObject.filename).replace('//','/'))
                continue
            
            fullName = '////{0}/{1}/{2}/{3}'.format(smbProxy.server, smbProxy.share, currentLocation, smbObject.filename).replace('//','/').lower()
            
            if not self.regex.search(smbObject.filename):
                self.logger.LogMessage('verbose','ignoring {0}'.format(fullName))
                continue

            if smbObject.file_size > self.settings.max_file_size_bytes:
                self.logger.LogMessage('verbose','ignoring too big {0}'.format(fullName))   
                continue
            
            size = smbObject.file_size
            shortName = smbObject.filename.lower()                    
            createTime = datetime.fromtimestamp(smbObject.create_time)
            updateTime = datetime.fromtimestamp(smbObject.last_write_time)

            if self.TurboCheckMetaExistanceCallback(createTime, updateTime, shortName, fullName):
                self.logger.LogMessage('verbose','[TURBO] meta found {0}'.format(fullName))
                continue

            fileData = smbProxy.RetrieveFile(currentLocation, smbObject.filename)

            if fileData:                    
                self.ProcessFileCallback(fileData, size, createTime, updateTime, shortName, fullName)        
                         
                    
                    


    


  


    
