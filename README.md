# cross-exchange-fee-spread

Track and compare fee differences across crypto exchanges.

## Goal

This project is for collecting, normalizing, and analyzing exchange fee data so we can quickly answer questions like:

- Which exchange has the lowest spot trading fee for a given account tier?
- How much does the effective cost change after maker/taker differences?
- Where do withdrawal fees or funding fees create hidden spread?

## Suggested Structure

- `collectors/`: exchange-specific data collectors
- `analysis/`: comparison, ranking, and spread calculations
- `src/`: shared models, utilities, and service code
- `tests/`: automated tests
- `docs/`: product notes and research
- `data/`: local snapshots or sample datasets
- `scripts/`: developer and maintenance scripts

## Next Steps

1. Drop the existing project code into this repository.
2. Tell me the stack you want to use, or let me inspect the codebase.
3. I can then wire up startup, lint, test, and GitHub sync.
