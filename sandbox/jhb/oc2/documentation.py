"""
This is documentation (and doctest) file. It shows how the API is used, and 
how the system is supposed to work.

Please have a look at doc/message_dump.txt, or turn on the transports.printmessages
below, and generate the output for yourself. The section headers in the output
are generated by the 'printSection' commands in this file.


>>> import transports
>>> from transports import DirectTransport as DT
>>> from transports import printSection

toggle printing of the messages
>>> transports.printmessages = 0



###############################################################################
Setup an issuer

>>> from issuer import Issuer
>>> issuer = Issuer({})
>>> issuer.createMasterKeys()



issuer sets up "currency description document" = CDD (like a root certificate)

>>> port = 9090
>>> denominations = [0,1,2,5,10,20]
>>> cdd = issuer.makeCDD('OpenCentA','oca',[str(d) for d in denominations],'http://localhost:%s/' % port,'')
>>> issuer.getMasterPubKey().verifyContainerSignature(cdd)
True



###############################################################################
mint (regularily) creates keypairs (pP,sP) for all denominations and id(p). 
Master key holder generates keys certificate

>>> from mint import Mint
>>> mint = Mint({})
>>> mint.setCDD(cdd)
>>> keys = mint.newMintKeys()
>>> mkcs = issuer.signMintKeys(keys=keys,cdd = cdd)
>>> issuer.getMasterPubKey().verifyContainerSignature(mkcs['20'])
True


>>> import storage

Wallet fetches cdd from issuer

>>> printSection('Basic Setup')

we could use the method directly
>>> from wallet import Wallet
>>> wallet = Wallet(storage.EmptyStorage())
>>> cdd == wallet.askLatestCDD(issuer.giveLatestCDD)
True

but its better to use more real transports
>>> import testutils
>>> transport = transports.HTTPTransport('http://localhost:%s/' % port)
>>> testutils.run_once(port,issuer)
>>> cdd2 = wallet.askLatestCDD(transport)
>>> cdd2.toString(True) == cdd.toString(True)
True



###############################################################################
Wallet: fetches current public minting keys for denomination


>>> printSection('Prepare Blinds')

>>> testutils.run_once(port,issuer)
>>> mkcs = wallet.fetchMintKeys(transport,cdd,denominations=['1','5'])
>>> mkcs[0].toString() == issuer.getCurrentMKCs()['1'].toString()
True



Wallet creates  blank and blinds it

>>> mkc = mkcs[1]
>>> cdd.masterPubKey.verifyContainerSignature(mkc)
True
>>> blank = wallet._makeBlank(cdd,mkc)
>>> blank.denomination == '5'
True
>>> key = mkc.publicKey
>>> secret, blind = key.blindBlank(blank)
>>> tid = wallet.makeSerial()
>>> int(mkc.denomination)
5



###############################################################################
Lets try to get a coin minted

We first need to setup an authorizer, to (surpise) authorize the request. Nils says
the mint should just mint

>>> from authorizer import Authorizer
>>> authorizer = Authorizer({})
>>> authpub = authorizer.createKeys() 
>>> mint.addAuthKey(authpub)
>>> authorizer.setMKCs(mkcs)

Lets have the authorizer denying the request

>>> printSection('Blinding I')

>>> authorizer.deny = True
>>> testutils.run_once(port,issuer=issuer,mint=mint,authorizer=authorizer)
>>> wallet.requestTransfer(transport,tid,'foo',[[mkc.keyId,blind]],[]).header
'TransferReject'

Now have a well working one

>>> printSection('Blinding II')

>>> authorizer.deny = False
>>> testutils.run_once(port,issuer=issuer,mint=mint,authorizer=authorizer)
>>> response = wallet.requestTransfer(transport,tid,'foo',[[mkc.keyId,blind]],[])
>>> response.header
'TransferAccept'

And check it

>>> blindsign = response.signatures[0]
>>> blank.signature = key.unblind(secret,blindsign)
>>> coin = blank
>>> key.verifyContainerSignature(coin)
True

We don't have a transport between mint and issuer yet. Lets have the mint
stuff coins directly into the issuer 

>>> mint.addToTransactions = issuer.addToTransactions

The mint can also be a bit slow

>>> printSection('Delay I')

>>> mint.delay = True
>>> testutils.run_once(port,issuer=issuer,mint=mint,authorizer=authorizer)
>>> wallet.requestTransfer(transport,tid,'foo',[[mkc.keyId,blind]],[]).header
'TransferDelay'

>>> mint.delay = False

Or the issuer is slow

>>> printSection('Delay II')

>>> issuer.delay = True
>>> testutils.run_once(port,issuer=issuer)
>>> wallet.resumeTransfer(transport,tid).header
'TransferDelay'
>>> issuer.delay = False

So we need to resume

>>> printSection('Resume')

>>> testutils.run_once(port,issuer=issuer)
>>> wallet.resumeTransfer(transport,tid).header
'TransferAccept'

And we have a valid coin

>>> blindsign = response.signatures[0]
>>> blank.signature = key.unblind(secret,blindsign)
>>> coin = blank
>>> key.verifyContainerSignature(coin)
True



###############################################################################
Now, wallet to wallet. We setup an alice and a bob side. Alice announces
a sum, and bob dedices if he wants to accept it

>>> printSection('W2W: Announce')
>>> alice = wallet
>>> bob = Wallet(storage.EmptyStorage())
>>> bob.approval = "I don't like odd sums"
>>> alicetid = alice.makeSerial()
>>> alice.announceSum(DT(bob.listenSum), alicetid, 5, 'foobar') 
"I don't like odd sums"

>>> bob.approval = True
>>> alice.announceSum(DT(bob.listenSum), alicetid, 5, 'foobar') 
True


Wallet Alice sends tokens to Wallet Bob (this time including their clear 
serial and signature)

For testing this we need to have a special transport that actually 
allows the two consecutive requests that bob needs to make

>>> tht = transports.TestingHTTPTransport(port,issuer=issuer,mint=mint)

>>> printSection('W2W: Rejected I')

Lets have first a wrong transactionId
>>> alice.requestSpend(DT(bob.listenSpend,tht),'foobar',[coin])
Traceback (most recent call last):
    ....
SpendReject: unknown transactionId

Or lets try to send a wrong amount

>>> printSection('W2W: Rejected II')
>>> alice.announceSum(DT(bob.listenSum), alicetid, 5, 'foobar')
True
>>> alice.requestSpend(DT(bob.listenSpend,tht),alicetid,[])
Traceback (most recent call last):
    ....
SpendReject: amount of coins does not match announced one. Announced: 5, got 0

And now, finally

>>> printSection('W2W: Success')
>>> alice.announceSum(DT(bob.listenSum), alicetid, 5, 'foobar')
True
>>> alice.requestSpend(DT(bob.listenSpend,tht), alicetid, [coin]) 
True

That was so fun, lets do it again

>>> printSection('W2W: Double Spend')
>>> alicetid = alice.makeSerial()
>>> bob.approval = True
>>> alice.announceSum(DT(bob.listenSum), alicetid, 5, 'foobar')
True
>>> alice.requestSpend(DT(bob.listenSpend,tht), alicetid, [coin])
Traceback (most recent call last):
    ....
SpendReject: did not go through


>>> printSection('Redeem')
>>> bobtid = wallet.makeSerial()
>>> testutils.run_once(port,issuer=issuer,mint=mint)
>>> bobscoins = bob.storage[cdd.currencyId]['coins']
>>> bob.requestTransfer(transport,tid,target='foo', coins = bobscoins).header
'TransferAccept'


"""


if __name__ == "__main__":
    import doctest
    doctest.testmod(optionflags=doctest.ELLIPSIS)
