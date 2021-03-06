"""This is a playground to develop the api for the pubkey and secret key.
Don't take the crypto seriously"""
from containerbase import *
import hashlib
import rsa

  

class KeyField(Field):
    
    def __init__(self,name,signing=True,isPrivate=False,default=''):
        Field.__init__(self,name=name,signing=signing,default=default)
        self.isPrivate = isPrivate

    def getencoded(self,object,allData=False):
        value = getattr(object,self.name,self.default)
        items = value.items()
        items.sort()
        #items = [(key,hex(val)) for key,val in items]
        return items

    def setdecoded(self,object,data):
        #data = [(key,int(val,0)) for key,val in data]
        setattr(object,self.name,dict(data))

class PubKey(Container):

    fields = [KeyField('key')]

    def encrypt(self,data):
        return rsa.encrypt(data,self.key)

    def verifySignature(self,signature,data):
        clear = rsa.verify(signature,self.key)
        return data == clear

    def verifyContainerSignature(self,container):
        signature = container.signature
        data = container.hash()
        return self.verifySignature(signature=signature,data=data)

    def createBlindingSecret(self):
        return rsa.getUnblinder(self.key['n'])

    def blind(self,data):
        secret = self.createBlindingSecret()
        blinder =  pow(rsa.invMod(secret, self.key['n']), self.key['e'], self.key['n'])
        blinded = rsa.blind(data,blinder,self.key)
        return secret, blinded

    def blindBlank(self,blank):
        return self.blind(blank.hash())

    def unblind(self,secret,data):
        number = data
        return (number * secret) % self.key['n']

class PrivKey(Container):
    
    fields = [KeyField('key')]

    def decrypt(self,data):
        return rsa.decrypt(data,self.key)

    def sign(self,data):
        return rsa.sign(data,self.key)

    def signblind(self,number):
        return rsa.encrypt_int(number,self.key['d'],self.key['n'])

    def signContainer(self,container):
        signature =  self.sign(container.hash())
        container.signature = signature
        return container

def hash(data):
    return rsa.bytes2int(hashlib.sha256(data).hexdigest())

def hashContainer(container,allData=False):
    return hash(container.toString(allData=allData))

def createSerial():
    return rsa.bytesToNumber(rsa.getRandomBytes(16))
#!!!
Container.hash = hashContainer

def KeyFactory(bitlen):
    pub,priv = rsa.gen_pubpriv_keys(bitlen)
    pubkey = PubKey()
    pubkey.key = pub
    privkey = PrivKey()
    privkey.key = priv
    return privkey,pubkey
 
if __name__ == '__main__':
    keys = KeyFactory(1024)
