# Solathon examples

Run these from the repository root after `poetry install --with dev --all-extras`, or from any environment where Solathon is installed.

```bash
poetry run python example/rpc.py
poetry run python example/versioned_transactions.py
poetry run python example/token_primitives.py
poetry run python example/solana_pay/main.py
```

None of those commands submits a transaction. The v1 sample is for local format testing only; public Solana clusters do not yet accept v1.

`send_transfer.py` is dry-run by default. It never contains or prints private-key material. Supply a CLI-compatible keypair file and recipient through arguments or environment variables:

```bash
export SOLANA_KEYPAIR="$HOME/.config/solana/id.json"
export SOLANA_RECIPIENT="<recipient-public-key>"
poetry run python example/send_transfer.py
```

The command above fetches a devnet blockhash and prints an unsigned wire
template that cannot authorize a transfer. Add `--send` only when you
deliberately want to sign and transfer real lamports on the configured RPC
cluster:

```bash
poetry run python example/send_transfer.py --send
```

Set `SOLANA_RPC_URL` to use another endpoint. Verify the endpoint and recipient before adding `--send`; neither Solathon nor this example can distinguish valuable mainnet funds from test funds.
