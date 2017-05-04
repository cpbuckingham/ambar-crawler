from datetime import datetime
from model import AmbarLogRecord
import sys

class AmbarLogger:
    def __init__(self, ApiProxy, LoggingId, Verbose):
        self.loggingId = LoggingId
        self.verbose = Verbose
        self.apiProxy = ApiProxy

    def SendLogMessageToES(self, MessageType, Message):
        try:
            apiResp = self.apiProxy.IndexLogRecord(AmbarLogRecord.Init(self.loggingId, MessageType, Message))
            if not (apiResp.Ok or apiResp.Created):
                print('{0}: [{1}] {2} {3}'.format(datetime.now(), 'error', apiResp.code, apiResp.message), file=sys.stderr)  
        except:
            print('{0}: [{1}] {2}'.format(datetime.now(), 'error', 'error submitting error to WebApi'), file=sys.stderr)  

    def LogMessage(self, MessageType, Message):
        """Writing message into stdout, stderr and ES (calling WebApi)
        MessageType: verbose, info, error
        All messages are logged into ES
        Error messages are logged into stderr
        Info messages are logged into stdout        
        If in config.json set "Verbose": true then all messages except for errors are logged into stdout    
        """
        if MessageType == 'error':
            print('{0}: [{3}] [{1}] {2}'.format(datetime.now(), MessageType, Message, self.loggingId), file=sys.stderr)
            self.SendLogMessageToES(MessageType, Message)
        elif MessageType == 'info' or self.verbose:
            print('{0}: [{3}] [{1}] {2}'.format(datetime.now(), MessageType, Message, self.loggingId), file=sys.stdout)
            self.SendLogMessageToES(MessageType, Message)