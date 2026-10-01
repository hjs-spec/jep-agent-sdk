# Contributing to JEP-Agent SDK

For SDK bugs or documentation problems, [open an issue here](https://github.com/hjs-spec/jep-agent-sdk/issues/new)
with the installed version, a minimal reproduction and expected/actual results.
Use the [shared contribution routes](https://github.com/hjs-spec/.github/blob/main/CONTRIBUTING.md)
for specification questions, independent implementations and interoperability reports.
Report security-sensitive findings [privately](https://github.com/hjs-spec/.github/blob/main/SECURITY.md).

## Setup

```bash
git clone https://github.com/hjs-spec/jep-agent-sdk.git
cd jep-agent-sdk
make install
python -m pip install jep-core-conformance==0.7.7
```

## Testing

```bash
make test
```

## Code Style

```bash
make format
make lint
```

## Pull Request Process

1. Ensure tests pass (`make test`)
2. Update examples if API changes
3. Update `CHANGELOG.md`
