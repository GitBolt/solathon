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

Solathon supports Python 3.10 and newer.
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

## RPC compatibility

`Client` and `AsyncClient` cover all standard HTTP methods in the current
[Solana RPC reference](https://solana.com/docs/rpc/http), including versioned
transactions, transaction simulation, prioritization fees, token queries, and
vote/stake queries.

## Priority fees

Compute budget instructions can be added before the other transaction instructions when the network is congested.

```python
from solathon.core import ComputeBudgetProgram

compute_limit = ComputeBudgetProgram.set_compute_unit_limit(200_000)
compute_price = ComputeBudgetProgram.set_compute_unit_price(1_000)
```

Add these instructions before the program instructions in the transaction.

# 🗃️ Contribution
Drop a pull request for anything which seems wrong or can be improved, could be a small typo or an entirely new feature! Checkout [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to proceed.
