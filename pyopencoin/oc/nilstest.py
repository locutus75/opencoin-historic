from entities import Wallet, IssuerEntity
from transports import ServerTestTransport, ClientTest
import tests
walletA = Wallet()
walletA.coins = [tests.coinB]

walletB = Wallet()
ie = tests.makeIssuerEntity()
t = ClientTest(walletB.listen,
                clientnick='walletA',
                autocontinue=1,
                autoprint='json',
                servernick='walletB')
t2 = ClientTest(ie.issuer.listen,
                clientnick='walletB',
                autocontinue=1,
                autoprint='json',
                servernick='issuer')

# setup things for walletB to be able to perform connection with issuer
walletB.addIssuerTransport(location=ie.issuer.getCDD().issuer_service_location, transport=t2)
walletB.setCurrentCDD(ie.issuer.getCDD())

walletA.sendCoins(t,amount=1,target='a book')





