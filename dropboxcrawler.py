import re
import io
from datetime import datetime
import dropbox
from dropbox.files import WriteMode, FolderMetadata, FileMetadata
from dropbox.exceptions import ApiError, AuthError
from filecrawler import FileCrawler
from model import AmbarCrawlerSettings, AmbarCrawlerSettingsCredentials, AmbarFileMeta
from logger import AmbarLogger

class DropboxCrawler(FileCrawler):      
    ## __init__() inherited from FileCrawler

    ## inherited method Crawl
    def Crawl(self):
        """Crawling folders from AmbarCrawlerSettings recursively
        """

        ## instantiatind Dropbox object
        dbx = dropbox.Dropbox(self.settings.credentials.token)

        try:
            dbx.users_get_current_account()
        except Exception as e:
           self.logger.LogMessage('error', 'error connecting to Dropbox {0}'.format(str(e)))
           return       

        ## iterating through locations
        for location in self.settings.locations: 
            self.logger.LogMessage('info', 'crawling {0}'.format(location.location))
            self.CrawlLocationRecursively(dbx, location.location)
        
        self.logger.LogMessage('info', 'done')

    def CrawlLocationRecursively(self, Dropbox, Location):
        try:
            listResult = Dropbox.files_list_folder(Location, recursive=True)
        except Exception as e:
            self.logger.LogMessage('error', 'error listing location {0} {1}'.format(Location, str(e)))
            return        
        
        for entry in listResult.entries:
            self.LocationEntryCallback(Dropbox, entry)

        while listResult.has_more:
            try:
                listResult = Dropbox.files_list_folder_continue(listResult.cursor)
            except Exception as e:
                self.logger.LogMessage('error', 'error listing location {0} {1}'.format(Location, str(e)))
                return
                
            for entry in listResult.entries:
                self.LocationEntryCallback(Dropbox, entry)

    def LocationEntryCallback(self, Dropbox, Entry):
        if type(Entry) is not FileMetadata:
            return

        if not self.regex.search(Entry.name):
            self.logger.LogMessage('verbose','ignoring {0}'.format(Entry.path_lower))
            return

        if Entry.size > self.settings.max_file_size_bytes:
            self.logger.LogMessage('verbose','ignoring too big {0}'.format(Entry.path_lower))   
            return

        size = Entry.size
        fullName = '//dropbox{0}'.format(Entry.path_lower).lower()
        shortName = Entry.name.lower()                    
        createTime = Entry.server_modified
        updateTime = Entry.server_modified

        if  self.TurboCheckMetaExistanceCallback(createTime, updateTime, shortName, fullName):
            self.logger.LogMessage('verbose','[TURBO] meta found {0}'.format(fullName))
            return
            
        try:
            response = Dropbox.files_download(Entry.path_lower)[1]
            fileStream = io.BytesIO(response.content)
        except Exception as e:
            self.logger.LogMessage('error', 'error retrieving file {0} {1}'.format(Entry.path_lower, str(e)))
            return
        
        self.ProcessFileCallback(fileStream, size, createTime, updateTime, shortName, fullName)