# AutoLab

AI agent searching for **solid electrolytes for lithium-metal batteries**: a Meta language model proposes chemical substitutions, the code builds the crystals, UMA (Meta FAIR) simulates them, scientific filters rank them, and the model reads the results to decide what to try next.

Built for the Meta Global AI Developer Hackathon (track "Push the Frontier", Indie).

## Install

```bash
pip install -e ".[bandgap,dev]"
cp .env.example .env   # then fill in the keys yourself
```

## Tests

```bash
pytest            # CPU tests; GPU and paid-API tests are skipped
pytest --gpu      # UMA tests (NVIDIA GPU only)
pytest --api      # real LLM calls (costs credits)
```

See `SPEC.md` for the architecture and validated parameters.
