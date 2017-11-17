from apiproxy import ApiProxy, RestApiResponse
from model import AmbarFileMeta,AmbarCrawlerSettings
from logger import AmbarLogger
from abc import *
from hashlib import sha256
import hashlib
import re

class FileCrawler:
    def __init__(self, ApiProxy, CrawlerSettings):
        """Initializing file crawler
        CrawlerSettings - AmbarCrawlerSettings object from model
        ApiProxy - initilized ApiProxy object
        """
        self.settings = CrawlerSettings
        self.apiProxy = ApiProxy
        self.regex = re.compile(self.settings.file_regex, re.I)
        self.logger = AmbarLogger(self.apiProxy, self.settings.uid, self.settings.verbose)
        self.logger.LogMessage('info', 'filecrawler initialized'.format(self.settings.uid))
    
    @abstractmethod
    def Crawl(self):
        """Crawling method
        Should call ProcessFileCallback() on every file that should be processed
        """
        pass
         
    def ProcessFileCallback(self, FileDataStream, FileSize, CreateTime, UpdateTime, ShortName, FullName):
        """Callback method for file crawler
        FileDataStream - ByteIO object
        """       
        fileMeta = AmbarFileMeta.Init(CreateTime, UpdateTime, ShortName, FullName, self.settings.id)

        sha = sha256(FileDataStream.getvalue()).hexdigest()

        ## checking content existance
        apiResp = self.apiProxy.CheckIfAmbarFileParsedContentExists(sha)

        if not apiResp.Success: 
            self.logger.LogMessage('error', 'error checking content existance {0} {1}'.format(fileMeta.full_name, apiResp.message))
            return

        if not (apiResp.Found or apiResp.NotFound):
            self.logger.LogMessage('error', 'unexpected response on checking content existance {0} {1} {2}'.format(fileMeta.full_name, apiResp.code, apiResp.message))
            return

        if apiResp.NotFound:
            self.logger.LogMessage('verbose', 'content not found {0}'.format(fileMeta.full_name))            

            ## creating content
            createContentApiResp = self.apiProxy.CreateAmbarFileContent(FileDataStream, sha)

            if not createContentApiResp.Success: 
                self.logger.LogMessage('error', 'error creating content {0} {1}'.format(fileMeta.full_name, createContentApiResp.message))
                return

            if not (createContentApiResp.Found or createContentApiResp.Created):
                self.logger.LogMessage('error', 'unexpected response on create content {0} {1} {2}'.format(fileMeta.full_name, createContentApiResp.code, createContentApiResp.message))
                return

            if createContentApiResp.Found:
                self.logger.LogMessage('verbose', 'content found {0}'.format(fileMeta.full_name))                

            if createContentApiResp.Created:
                self.logger.LogMessage('verbose', 'content created {0}'.format(fileMeta.full_name))                
        
        if apiResp.Found:       
            self.logger.LogMessage('verbose', 'content found {0}'.format(fileMeta.full_name))

        ## sending meta to pipeline
        apiResp = self.apiProxy.AddAmbarFileMeta(fileMeta, sha, FileSize, self.settings.index_name, self.settings.uid)

        if not apiResp.Success:
            self.logger.LogMessage('error', 'error adding meta {0} {1}'.format(fileMeta.full_name, apiResp.message)) 
            return
        
        if apiResp.BadRequest:
            self.logger.LogMessage('verbose', 'bad meta, ignoring... {0}'.format(fileMeta.full_name))
            return

        if apiResp.InsufficientStorage:
            raise Exception('insufficient storage')
            return
        
        if not apiResp.Ok:
            self.logger.LogMessage('error', 'unexpected response on adding meta {0} {1} {2}'.format(fileMeta.full_name, apiResp.code, apiResp.message))
            return
        
        self.logger.LogMessage('verbose', 'meta added {0}'.format(fileMeta.full_name))          
        

    def TurboCheckMetaExistanceCallback(self, CreateTime, UpdateTime, ShortName, FullName):
        """Callback method for turbo checking meta existance
        """
        amFileMeta = AmbarFileMeta.Init(CreateTime, UpdateTime, ShortName, FullName, self.settings.id)
        apiResp = self.apiProxy.CheckIfAmbarFileMetaExists(amFileMeta, self.settings.index_name)

        if not apiResp.Success:
            self.logger.LogMessage('error', 'error checking meta existance {0} {1}'.format(FullName, apiResp.message)) 
            return None

        if apiResp.Ok:
            return True

        if apiResp.NotFound:
            return False  

        self.logger.LogMessage('error', 'unexpected response on turbo check meta existance {0} {1} {2}'.format(FullName, apiResp.code, apiResp.message))

        return None                    