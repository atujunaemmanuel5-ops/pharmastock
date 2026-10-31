# Safety rules implemented

PharmaStock AI is decision support for a licensed dispenser. The deterministic
rules decide; the assistant can only retrieve and explain cited text.

The cart decision order is:

1. Unknown catalogue item: `UNKNOWN`; the cart cannot be assessed.
2. A sourced prescription-required item without a reference: `BLOCK`.
3. No unexpired batch: `BLOCK`. Expired stock is never eligible.
4. Major interaction: `STOP`. A pharmacist can proceed only with a reason,
   which is returned as `STOP_OVERRIDDEN` and must be logged by a real adapter.
5. Moderate interaction or same ATC level-4 duplication: `WARN`.
6. Near-expiry unexpired stock: `INFO` and a FEFO batch suggestion.
7. Otherwise: `OK`.

`UNKNOWN` and `BLOCK` outrank `STOP`, which outranks `WARN`, `INFO`, and `OK`.
The current catalogue keeps proposed prescription rows visible for pharmacist
review but only enforces rows with a source reference. Misoprostol is the demo
source-backed example. The prescription reference is checked for presence; it
is not verified against an e-prescription service.

Missing DDInter pairs are reported as no pair in the imported development data,
not as “safe”. Interaction data and all inventory/drug-level numbers in this
repository are demonstration data and require pharmacist verification before
operational use.
