<p align="center">
  <a href="#">
    <img
      alt="Solathon logo"
      src="https://solathon.vercel.app/solathon.svg"
      width="140"
    />
  </a>
</p>


<p align="center">
  <a href="https://pypi.org/project/solathon/" target="_blank"><img src="https://badge.fury.io/py/solathon.svg" alt="PyPI version"></a>
  <a href="https://github.com/GitBolt/solathon/blob/master/LICENSE" target="_blank"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT License"></a>
  <br>
</p>

<h1 align="center">Solathon</h1>

Solathon is a high performance, easy to use and feature-rich Solana SDK for Python. Easy for beginners, powerful for real world applications.

# ✨ Getting started
## Installation
```
pip install solathon
```
## Client example
```python
from solathon import Client

client = Client("https://api.devnet.solana.com")
```
## Basic usage example
```python
# Basic example of fetching a public key's balance
from solathon import Client, PublicKey

client = Client("https://api.devnet.solana.com")
public_key = PublicKey("B3BhJ1nvPvEhx3hq3nfK8hx4WYcKZdbhavSobZEA44ai")

balance = client.get_balance(public_key)
print(balance)
```

## ⏱ Handling Congestion with Compute Budget Instructions

On Solana, transaction fees are based on compute units consumed. During high network load, your transaction may fail or be delayed unless additional compute resources are allocated.

You can manually increase the compute unit limit and the price per unit using Solathon's `ComputeBudgetProgram`. This is especially useful when the network is congested.

```python
from solathon import Client, Transaction, PublicKey, Keypair
from solathon.core.instructions import transfer
from solathon.core import ComputeBudgetProgram

client = Client("https://api.devnet.solana.com")
sender = Keypair()
receiver = PublicKey("DESTINATION_PUBLIC_KEY")

# Optional: Increase compute resources
compute_limit_ix = ComputeBudgetProgram.set_compute_unit_limit(1_000_000)
compute_price_ix = ComputeBudgetProgram.set_compute_unit_price(1)  # micro-lamports per unit

# Transfer instruction
transfer_ix = transfer(from_public_key=sender.public_key, to_public_key=receiver, lamports=10_000)

# Create and send transaction
tx = Transaction(
    instructions=[compute_limit_ix, compute_price_ix, transfer_ix],
    signers=[sender]
)
result = client.send_transaction(tx)
print("Transaction signature:", result)
```

# 🗃️ Contribution
Drop a pull request for anything which seems wrong or can be improved, could be a small typo or an entirely new feature! Checkout [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to proceed.
