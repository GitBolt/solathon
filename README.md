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
  <a href="https://github.com/SuperteamDAO/solathon/blob/master/LICENSE" target="_blank"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="MIT License"></a>
  <br>
</p>

<h1 align="center">Solathon</h1>

Solathon is a high performance, easy to use and feature-rich Solana SDK for Python. Easy for beginners, powerful for real world applications. **Fully compatible with Solana Agave v2.0.**

# ✨ Getting started
## Installation
```
pip install solathon
```
## Client example
```python
from solathon import Client

# Works with any RPC endpoint — devnet, mainnet, or custom (Helius, QuickNode, etc.)
client = Client("https://api.devnet.solana.com")
```
## Basic usage example
```python
from solathon import Client, PublicKey

client = Client("https://api.devnet.solana.com")
public_key = PublicKey("B3BhJ1nvPvEhx3hq3nfK8hx4WYcKZdbhavSobZEA44ai")

balance = client.get_balance(public_key)
print(balance)
```

# 📋 Supported RPC Methods

All methods are available on both `Client` (sync) and `AsyncClient` (async).

### Account
| Method | Description |
|--------|-------------|
| `get_account_info` | Returns all account info for a public key |
| `get_balance` | Returns lamport balance |
| `get_multiple_accounts` | Returns account info for multiple keys |
| `get_program_accounts` | Returns all accounts owned by a program |
| `get_largest_accounts` | Returns 20 largest accounts by balance |
| `get_minimum_balance_for_rent_exemption` | Min balance for rent exemption |

### Block
| Method | Description |
|--------|-------------|
| `get_block` | Returns block info for a slot |
| `get_block_height` | Current block height |
| `get_block_production` | Block production info |
| `get_block_commitment` | Commitment for a block |
| `get_blocks` | List of confirmed blocks in range |
| `get_blocks_with_limit` | Confirmed blocks from start slot |
| `get_block_time` | Estimated production time of a block |
| `get_latest_blockhash` | Latest blockhash |
| `is_blockhash_valid` | Check if blockhash is still valid |

### Cluster & Node
| Method | Description |
|--------|-------------|
| `get_cluster_nodes` | All nodes in the cluster |
| `get_epoch_info` | Current epoch info |
| `get_epoch_schedule` | Epoch schedule |
| `get_first_available_block` | Lowest confirmed block |
| `get_genesis_hash` | Genesis hash |
| `get_health` | Node health status |
| `get_identity` | Node identity pubkey |
| `get_version` | Node software version |
| `get_highest_snapshot_slot` | Highest snapshot slot |
| `get_leader_schedule` | Leader schedule for epoch |
| `get_max_retransmit_slot` | Max retransmit slot |
| `get_max_shred_insert_slot` | Max shred insert slot |
| `get_slot` | Current slot |
| `get_slot_leader` | Current slot leader |
| `get_slot_leaders` | Slot leaders for range |
| `minimum_ledger_slot` | Min slot in ledger |
| `get_vote_accounts` | Vote account info |
| `get_recent_performance_samples` | Recent performance samples |

### Transaction
| Method | Description |
|--------|-------------|
| `get_transaction` | Transaction details by signature |
| `get_transaction_count` | Total transaction count |
| `get_signatures_for_address` | Transaction signatures for an address |
| `get_signature_statuses` | Statuses for transaction signatures |
| `send_transaction` | Sign and send a transaction |
| `simulate_transaction` | Simulate without broadcasting |
| `request_airdrop` | Request SOL airdrop (devnet/testnet) |

### Token (SPL)
| Method | Description |
|--------|-------------|
| `get_token_accounts_by_owner` | SPL token accounts by owner |
| `get_token_accounts_by_delegate` | SPL token accounts by delegate |
| `get_token_account_balance` | Token balance of an account |
| `get_token_supply` | Total supply of an SPL token |
| `get_token_largest_accounts` | Top 20 holders of an SPL token |

### Fees & Staking
| Method | Description |
|--------|-------------|
| `get_fee_for_message` | Fee for a message |
| `get_recent_prioritization_fees` | Recent priority fee data |
| `get_stake_minimum_delegation` | Minimum stake delegation |

### Inflation & Supply
| Method | Description |
|--------|-------------|
| `get_inflation_governor` | Inflation governor |
| `get_inflation_rate` | Current inflation rate |
| `get_inflation_reward` | Staking rewards for addresses |
| `get_supply` | SOL supply info |

# 🔑 Keypair & Transaction

```python
from solathon import Keypair, Transaction, PublicKey
from solathon.core.instructions import transfer

# Generate new keypair
sender = Keypair()
print(f"Public key: {sender.public_key}")

# Or load from private key
sender = Keypair.from_private_key("your_base58_private_key")

# Or from Solana CLI JSON file
sender = Keypair.from_file("~/.config/solana/id.json")

# Build and send a transfer
receiver = PublicKey("ReceiverPublicKeyHere")
instruction = transfer(sender.public_key, receiver, lamports=1000000)

transaction = Transaction(instructions=[instruction], signers=[sender])
client.send_transaction(transaction)
```

# ⚡ Async Client

```python
import asyncio
from solathon import AsyncClient

async def main():
    client = AsyncClient("https://api.devnet.solana.com")
    balance = await client.get_balance("B3BhJ1nvPvEhx3hq3nfK8hx4WYcKZdbhavSobZEA44ai")
    print(balance)

asyncio.run(main())
```

# 💸 Solana Pay

```python
from solathon.solana_pay import encode_url

url = encode_url(recipient="ReceiverPubkey", amount=1.5, label="My Store")
```

# 🗃️ Contribution
Drop a pull request for anything which seems wrong or can be improved, could be a small typo or an entirely new feature! Checkout [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on how to proceed.
