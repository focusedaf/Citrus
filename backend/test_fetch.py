import requests, os
from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv("ETHERSCAN_KEY")
address = "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045"

# txtlist returns both 'Incoming'and 'Outgoing' transactions
url = (
    "https://api.etherscan.io/v2/api"
    f"?chainid=1"
    f"&module=account&action=txlist&address={address}"
    f"&sort=desc&apikey={API_KEY}"
)
resp = requests.get(url).json()
transactions = resp["result"]

# filter only outgoing transactions 
outgoing = [tx for tx in transactions if tx["from"].lower() == address.lower()]

print(f"Total transactions: {len(transactions)}")
print(f"Outgoing transactions: {len(outgoing)}")

for tx in outgoing[:5]:
    value_eth = int(tx["value"]) / 1e18
    print(f"To: {tx['to']} | Value: {value_eth} ETH | Hash: {tx['hash']}")