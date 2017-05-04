import imaplib
import email
import email.generator
import os

def normalizeFileName(filename):
    return "".join([str(c) for c in filename if str(c).isalpha() or str(c).isdigit() or str(c)==' ']).rstrip()

def decodeFileName(header):
    result = None

    try:
        res = email.header.decode_header(header)
        h,e = res[0]           
        header = h
        if (e == 'unknown-8bit'):
            result = str(num)
        elif (e != None):    
            result = h.decode(e)
    except:
        print('Can not decode')
        return result
    
    return result


mail = imaplib.IMAP4_SSL('imap.gmail.com')
mail.login('', '')

mail.select()

result, data = mail.uid('search', None, "ALL") # search and return uids instead
latest_email_uid = data[0].split()[-1]

for num in data[0].split():        
        rv, data = mail.fetch(num, '(RFC822)')
        if rv != 'OK' and data[0] != None:
            print("ERROR getting message", num)
            exit()
        raw_email = data[0][1]
        email_message = email.message_from_bytes(raw_email)
        
        decodedFileName = decodeFileName(email_message.get('Subject'))
        filename = normalizeFileName(decodedFileName if decodedFileName != None else str(num))
        
        print("Writing message ", filename)
        f = open('Messages\{0}.eml'.format(filename), 'wb')
        f.write(raw_email)
        f.close()

        if email_message.get_content_maintype() != 'multipart':
            continue
        idx = 0
        for part in email_message.walk():
            if part.get_content_maintype() == 'multipart':
                continue
            if part.get('Content-Disposition') is None:
                continue

            print(part.get_filename())
            partFilename = part.get_filename()
            if partFilename is not None:
                decodedFileName = decodeFileName(partFilename)
                
                sv_path = os.path.join('Messages', "{0}_{1}".format(filename, decodedFileName if decodedFileName != None else partFilename))                                 
            if not os.path.isfile(sv_path):
                payload = part.get_payload(decode=True)
                if payload == None:
                    continue

                print(sv_path)
                fp = open(sv_path, 'wb')
                fp.write(payload)
                fp.close()
            idx = idx + 1

mail.close()
mail.logout()