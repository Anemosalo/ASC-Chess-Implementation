# ASC-Chess-Implementation

Alias Stash Coding (ASC) applied to chess games. This is the code behind the paper
*Alias Stash Coding: Recycling the Unused Codewords of Fixed-Length Codes*.

## The idea

Each move is stored as its index among the legal moves of the position, sorted by UCI string.
With K legal moves, a fixed-length index takes b = ⌈log₂ K⌉ bits and leaves 2^b − K codewords
unused. ASC gives each unused codeword to one of the first moves as a second spelling, its alias.
Choosing between the two spellings is a free bit, and that bit carries the first bit of the next
codeword, which is then written one bit shorter.

The decoder always knows how many bits to read before reading them. On every game, ASC is exactly
as long as truncated binary or one bit longer.

## Running it

You need Python 3.9 or newer and python-chess 1.11.2:

```bash
pip install chess==1.11.2
```

Then, from this folder:

```bash
python3 roundtrip.py    # encodes and decodes every game; the last line should be 1083/1083
python3 benchmark.py    # bits per move for each method
```

`benchmark.py` gives the numbers in the paper's Table 1:

```
Method                      bits/ply  bits/game
Naive                         5.2386     444.36
Truncated binary              4.7866     406.01
ASC                           4.7917     406.44
TB incl. byte container       4.8621     412.42
ASC incl. byte container      4.8667     412.81
Mixed-radix bound             4.7323     401.40

Identity ASC - TB = E holds in 1083/1083 games (E = 1 in 471)
```

## Files

| File | What it does |
| --- | --- |
| `encoder.py` | The encoder. `resolve_chain` looks ahead to the end of each alias chain: every codeword in a chain starts with the same bit as the last one, so it reads that bit and assigns the chain in one pass. |
| `decoder.py` | The decoder. It reads each move's field at a width it already knows and never looks ahead. |
| `board_state.py` | The sorted legal moves of a position and its K, b and U. The encoder and decoder both use it, so they always see the same move order. |
| `bit_io.py` | Bit writer and reader. The stream ends with a 3-bit count of the valid bits in the last byte, so the decoder knows where the moves stop. |
| `benchmark.py` | Compares the naive code, truncated binary, ASC and the mixed-radix bound. |
| `roundtrip.py` | Checks that decoding gives back every game exactly. |
| `games_getter.py` | Downloads games from the chess.com public API into `games_archive/`. |

## Data

`games_archive/` holds the 1,083 games used in the paper (91,863 moves): Hikaru Nakamura's games from
February–March 2025 and Magnus Carlsen's from April–May 2025, from the chess.com public API. Each line
is one game, with its moves as comma-separated UCI strings.
