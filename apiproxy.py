import requests

class ApiProxy:
    def __init__(self, Name, ApiUrl, ApiCallTimeoutSeconds, ApiToken):
        self.name = Name
        self.apiUrl = ApiUrl
        self.apiCallTimeoutSeconds = ApiCallTimeoutSeconds
        self.headers = {'ambar-email': Name, 'ambar-email-token': ApiToken}
    
    def CheckIfAmbarFileParsedContentExists(self, Sha):
        apiResp = RestApiResponse()
        try:
            apiUri = '{0}/api/files/content/{1}/parsed'.format(self.apiUrl, Sha)
            req = requests.head(apiUri, headers=self.headers, timeout = self.apiCallTimeoutSeconds)
            apiResp.result = 'ok'
            apiResp.code = req.status_code            
        except requests.exceptions.RequestException as ex:
            apiResp.result = 'error'
            apiResp.message = str(ex)
        return apiResp   

    def CheckIfAmbarFileMetaExists(self, AmbarFileMeta, IndexName):
        apiResp = RestApiResponse()
        try:
            apiUri = '{0}/api/files/meta/exists/{1}'.format(self.apiUrl, IndexName)
            req = requests.post(apiUri, headers=self.headers, json = AmbarFileMeta.Dict, timeout = self.apiCallTimeoutSeconds)
            try:
                apiResp.message = req.text
            except:
                pass
            apiResp.result = 'ok'
            apiResp.code = req.status_code            
        except requests.exceptions.RequestException as ex:
            apiResp.result = 'error'
            apiResp.message = str(ex)
        return apiResp   
    
    def AddAmbarFileMeta(self, AmbarFileMeta, Sha, FileSize, IndexName, CrawlerUid):
        apiResp = RestApiResponse()
        try:
            apiUri = '{0}/api/files/meta/{1}/{2}/{3}/{4}'.format(self.apiUrl, IndexName, Sha, FileSize, CrawlerUid)
            req = requests.post(apiUri, headers=self.headers, json = AmbarFileMeta.Dict, timeout = self.apiCallTimeoutSeconds)
            try:
                apiResp.message = req.text
            except:
                pass
            apiResp.result = 'ok'
            apiResp.code = req.status_code            
        except requests.exceptions.RequestException as ex:
            apiResp.result = 'error'
            apiResp.message = str(ex)
        return apiResp
    
    def CreateAmbarFileContent(self, FileStream, Sha256):
        apiResp = RestApiResponse()
        try:
            apiUri = '{0}/api/files/content/{1}'.format(self.apiUrl, Sha256)
            files = {'file': (Sha256, FileStream.getvalue())}
            req = requests.post(apiUri, headers=self.headers, files = files, timeout = self.apiCallTimeoutSeconds)
            try:
                apiResp.message = req.text
            except:
                pass
            apiResp.result = 'ok'
            apiResp.code = req.status_code            
        except requests.exceptions.RequestException as ex:
            apiResp.result = 'error'
            apiResp.message = str(ex)
        return apiResp

    def IndexLogRecord(self, AmbarLogRecord):
        apiResp = RestApiResponse()
        try:
            apiUri = '{0}/api/logs'.format(self.apiUrl)
            req = requests.post(apiUri, headers=self.headers, json = AmbarLogRecord.Dict, timeout = self.apiCallTimeoutSeconds)
            try:
                apiResp.message = req.text
            except:
                pass
            apiResp.result = 'ok'
            apiResp.code = req.status_code            
        except requests.exceptions.RequestException as ex:
            apiResp.result = 'error'
            apiResp.message = str(ex)
        return apiResp

    def GetAmbarCrawlerSettings(self, CrawlerUid):
        apiResp = RestApiResponse()
        try:
            apiUri = '{0}/api/crawlers/settings/uid/{1}'.format(self.apiUrl, CrawlerUid)
            req = requests.get(apiUri, headers=self.headers, timeout = self.apiCallTimeoutSeconds)  
            if req.status_code == 200:
                apiResp.payload = req.json()
            else:
                try:
                    apiResp.message = req.text
                except:
                    pass     
            apiResp.result = 'ok'
            apiResp.code = req.status_code            
        except requests.exceptions.RequestException as ex:
            apiResp.result = 'error'
            apiResp.message = str(ex)
        return apiResp
    
    def ReportStarted(self, Uid):
        apiResp = RestApiResponse()
        try:
            apiUri = '{0}/api/crawlers/report/start/{1}'.format(self.apiUrl, Uid)
            req = requests.post(apiUri, headers=self.headers, timeout = self.apiCallTimeoutSeconds)
            try:
                apiResp.message = req.text
            except:
                pass
            apiResp.result = 'ok'
            apiResp.code = req.status_code            
        except requests.exceptions.RequestException as ex:
            apiResp.result = 'error'
            apiResp.message = str(ex)
        return apiResp
    
    def ReportFinished(self):
        apiResp = RestApiResponse()
        try:
            apiUri = '{0}/api/crawlers/report/finish'.format(self.apiUrl)
            req = requests.post(apiUri, headers=self.headers, timeout = self.apiCallTimeoutSeconds)
            try:
                apiResp.message = req.text
            except:
                pass
            apiResp.result = 'ok'
            apiResp.code = req.status_code            
        except requests.exceptions.RequestException as ex:
            apiResp.result = 'error'
            apiResp.message = str(ex)
        return apiResp

class RestApiResponse:
    def __init__(self):
        self.result = 'ok'
        self.code = 0
        self.payload = None
        self.message = None

    @property
    def Success(self):
        return True if self.result == 'ok' else False 
    @property
    def Error(self):
        return True if self.result == 'error' else False 

    @property
    def Ok(self):
        return True if self.code == 200 else False    
    @property
    def Created(self):
        return True if self.code == 201 else False  
    @property
    def NoContent(self):
        return True if self.code == 204 else False   
    @property
    def Found(self):
        return True if self.code == 302 else False
    @property
    def BadRequest(self):
        return True if self.code == 400 else False
    @property
    def Unauthorized(self):
        return True if self.code == 401 else False
    @property
    def NotFound(self):
        return True if self.code == 404 else False
    @property
    def Conflict(self):
        return True if self.code == 409 else False
    @property
    def InternalServerError(self):
        return True if self.code == 500 else False
    @property
    def InsufficientStorage(self):
        return True if self.code == 507 else False