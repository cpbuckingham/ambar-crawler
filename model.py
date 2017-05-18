from datetime import datetime
import os
from apiproxy import ApiProxy
import io
import json

class AmbarLogRecord:
    def __init__(self):
        self.created_datetime = datetime.now()
        self.indexed_datetime = datetime.now() 
        self.source_id = ''
        self.type = ''
        self.message = ''
    
    @classmethod
    def Init(cls, SourceId, Type, Message):
        logRecord = cls()
        logRecord.created_datetime = datetime.now()
        logRecord.indexed_datetime = datetime.now() 
        logRecord.source_id = str(SourceId)
        logRecord.type = str(Type)
        logRecord.message = str(Message)
        return logRecord
    
    def __iter__(self):
        yield 'created_datetime', self.created_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        yield 'indexed_datetime', self.indexed_datetime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        yield 'source_id', self.source_id
        yield 'type', self.type
        yield 'message', self.message
    
    @property
    def Dict(self):
        return dict(self)

class AmbarCrawlerSettings:
    def __init__(self):
        self.id = ''
        self.type = ''
        self.uid = ''
        self.index_name = ''
        self.description = ''
        self.locations = []
        self.file_regex = ''
        self.credentials = None
        self.max_file_size_bytes = 200000000
        self.verbose = False
        self.api_token = ''
    
    @classmethod
    def Init(cls, Payload):
        crawlerSettings = cls()
        crawlerSettings.id = Payload['id']
        crawlerSettings.type = Payload['type']
        crawlerSettings.uid = Payload['uid']
        crawlerSettings.index_name = Payload['index_name']
        crawlerSettings.description = Payload['description']
        crawlerSettings.locations = []
        for location in Payload['locations']:
            crawlerSettings.locations.append(AmbarCrawlerSettingsLocation.Init(location))
        crawlerSettings.file_regex = Payload['file_regex']
        crawlerSettings.credentials = AmbarCrawlerSettingsCredentials.Init(Payload['credentials'])
        crawlerSettings.max_file_size_bytes = Payload['max_file_size_bytes']
        crawlerSettings.verbose = Payload['verbose']
        return crawlerSettings

    def __iter__(self):
        yield 'id', self.id
        yield 'uid', self.uid
        yield 'index_name', self.index_name
        yield 'type', self.type
        yield 'description', self.description
        yield 'locations', self.locations
        yield 'file_regex', self.file_regex
        yield 'credentials', dict(self.credentials)
        yield 'max_file_size_bytes', self.max_file_size_bytes
        yield 'verbose', self.verbose

class AmbarCrawlerSettingsCredentials:
    def __init__(self):
        self.auth_type = ''
        self.login = ''
        self.password = ''
        self.token = ''
    
    @classmethod
    def Init(cls, Credentials):
        crawlerSettingsCredentials = cls()
        crawlerSettingsCredentials.auth_type = Credentials['auth_type']
        crawlerSettingsCredentials.login = Credentials['login']
        crawlerSettingsCredentials.password = Credentials['password']
        crawlerSettingsCredentials.token = Credentials['token']
        return crawlerSettingsCredentials
    
    def __iter__(self):
        yield 'auth_type', self.auth_type
        yield 'login', self.login
        yield 'password', self.password
        yield 'token', self.token

class AmbarCrawlerSettingsLocation:
    def __init__(self):
        self.host_name = ''
        self.ip_address = ''
        self.location = ''
    
    @classmethod
    def Init(cls, Location):
        crawlerSettingsLocation = cls()
        crawlerSettingsLocation.host_name = Location['host_name']
        crawlerSettingsLocation.ip_address = Location['ip_address']
        crawlerSettingsLocation.location = Location['location']
        return crawlerSettingsLocation

class AmbarFileExtra:
    def __init__(self):
        self.type = ''
        self.value = ''
    
    def __iter__(self):
        yield 'type', self.type
        yield 'value', self.value

class AmbarFileMeta:
    def __init__(self):
        self.full_name = ''
        self.short_name = ''
        self.extension = ''
        self.extra = []
        self.source_id = ''
        self.created_datetime = ''
        self.updated_datetime = ''     
        ## non serializable content
        self.initialized = False
        self.message = ''

    @classmethod
    def Init(cls, CreateTime, UpdateTime, ShortName, FullName, AmbarCrawlerId):
        """Full init with content import and sha256 calculation
        """
        amFileMeta = cls()
        try:            
            amFileMeta.full_name = FullName
            amFileMeta.short_name = ShortName
            amFileMeta.extension = os.path.splitext(ShortName)[1] if os.path.splitext(ShortName)[1] != '' else os.path.splitext(ShortName)[0]
            amFileMeta.extra = []
            amFileMeta.source_id = AmbarCrawlerId            
            if type(CreateTime) is str:
                amFileMeta.created_datetime = CreateTime
            else:
                amFileMeta.created_datetime = CreateTime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            if type(UpdateTime) is str:
                amFileMeta.updated_datetime = UpdateTime
            else:
                amFileMeta.updated_datetime = UpdateTime.strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]       
            ## non serializable content           
            amFileMeta.initialized = True
            amFileMeta.message = 'ok'        
        except Exception as ex:
            amFileMeta.initialized = False
            amFileMeta.message = str(ex) 
        return amFileMeta                

    def __iter__(self):
        yield 'full_name', self.full_name
        yield 'short_name', self.short_name
        yield 'extension', self.extension
        extraArr = []
        for extra in self.extra:
            extraArr.append(dict(extra))
        yield 'extra', extraArr
        yield 'source_id', self.source_id
        yield 'created_datetime', self.created_datetime
        yield 'updated_datetime', self.updated_datetime
    
    @property
    def Dict(self):
        return dict(self)