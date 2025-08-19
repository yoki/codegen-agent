# CodeGen Agent

LLM-assisted data analysis that can:
- Generate Python code from a natural-language request
- Execute the code against *your* variables in a disposable Docker container (root-in-container), with inputs mounted read-only and outputs mounted read-write
- Optionally provide IPython/Jupyter UX; otherwise use `core/*` programmatically

Use as a Python library.