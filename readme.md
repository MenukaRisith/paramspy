# 🕵‍♂ paramspy: Smart Parameter Discovery Tool

### Stop Brute-Forcing Noise. Start Spying on Targets.

| Version | Python | License | Status |
| :---: | :---: | :---: | :---: |
| [![PyPI](https://img.shields.io/pypi/v/paramspy.svg)](https://pypi.org/project/hsignal-paramspy/) | [![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/) | [![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE) | *Ready for Bug Bounty* |

*paramspy* is an ultra-fast, high-signal reconnaissance tool that automates the discovery of hidden and target-specific parameters by analyzing *10+ years of Wayback Machine data*. It bypasses the time-wasting process of running massive, generic wordlists, providing you with a clean, actionable list of production-used parameters in seconds.

---

## ✨ Why paramspy is a Game Changer

Traditional parameter discovery methods suffer from a low signal-to-noise ratio, wasting time and often missing unique bugs.

| Feature | Generic Wordlists (e.g., 60k lines) | *paramspy (Targeted ~200-800 lines)* |
| :--- | :--- | :--- |
| *Source Data* | Random, common junk | *Target-specific* Wayback URLs (10+ years) |
| *Signal-to-Noise* | Low (Drowning in false positives) | *High* (Real, validated production parameters) |
| *Time Saved* | Minimal (Slow brute-force) | *Saves 15–45 minutes per target* |
| *Killer Feature* | None | Seamless *Gf-pattern integration* |
| *Performance* | Slow | *Instant* (Uses cache and clean list) |

---

## ⚡ Installation

paramspy is available on PyPI and supports Python 3.9+.

```bash
# 1. Install the package
pip install paramspy

# 2. Recommended: Ensure you have a fuzzer (like ffuf) and gf installed
# go install [github.com/ffuf/ffuf@latest](https://github.com/ffuf/ffuf@latest)
# go install [github.com/tomnomnom/gf@latest](https://github.com/tomnomnom/gf@latest)
```

---

## 📖 Usage & Examples
1. Basic Scan & Piping
The default mode outputs a clean list directly to stdout, perfect for piping into your favorite fuzzing tools.

```bash
# Get the high-signal parameter list for the target
paramspy shopify.com

# Pipe the clean list directly into ffuf
paramspy tesla.com | ffuf -u "[https://tesla.com/v1/api/FUZZ](https://tesla.com/v1/api/FUZZ)" -w - -mc 200

# Pipe the clean list into arjun
paramspy example.com > params.txt
arjun -u [https://example.com](https://example.com) -i params.txt
```

2. The Killer Feature: Gf-Pattern Tagging (JSON Output)
Use the --output json flag to get a structured output, and then use jq to filter parameters tagged for specific vulnerability classes (like redirect or xss).

```bash
# 1. Run scan and get structured JSON output
paramspy target.com --output json > results.json

# 2. Use jq to extract only parameters related to redirects (HIGH PRIORITY!)
# This is equivalent to running 'gf redirect' but on a target-specific wordlist.
cat results.json | jq '.parameters[] | select(.tags[] | contains("redirect")) | .param' -r

# Example Output (Gold for Open Redirects/SSRF)
# redirect_uri
# return_to
# callback
# next
```

3. Cache Management
`paramspy` uses a local SQLite cache (`~/.paramspy/cache/`) to make repeated scans instant.

```bash
# Check status of all cached domains
paramspy cache status

# Clear the cache for a specific domain
paramspy cache clear tesla.com

# Clear the entire cache
paramspy cache clear
```

---

## ⚙️ Core Technology

- **Asynchronous Fetching:** Uses `httpx` for fast, concurrent fetching from the Wayback CDX API.

- **Intelligent Parsing:** Robust regex and `urllib.parse` handle standard, matrix, and encoded parameters.

- **Reliable CLI:** Built with Typer and provides beautiful terminal output and progress bars via Rich.

- **Production Caching:** Uses SQLite for performance, integrity, and simple TTL management.

---

## 🤝 Contribution

We welcome contributions! The most valuable contribution is expanding the high-signal built-in wordlist (`paramspy/data/builtin_params.json`). If you found a unique, non-generic parameter that led to a successful bug bounty submission, please open a Pull Request to add it!

1. Fork the repository.
2. Create your feature branch (`git checkout -b feature/new-parser`).
3. Commit your changes (`git commit -am 'Feat: Add new regex for complex URLs'`).
4. Push to the branch (`git push origin feature/new-parser`).
5. Create a new Pull Request.

---

## 📜 License

Distributed under the MIT License. See `LICENSE` for more information.