# Decoding speed: truncated binary against ASC

A short test of one question from the paper. ASC's decoder knows each field's width before reading
it. Does that make decoding faster than truncated binary (TB), whose decoder finds a codeword's
length while reading it?

This is a short test, not a study of decoder engineering. It uses synthetic messages, hand-written
decoders, one machine and one compiler. Other readers, machines and domains may give other results.
The code is here so that anyone can check it and try other settings. `AI_DISCLOSURE.md` says how it
was made.

## Run it

You need a C compiler. On AArch64 (Apple silicon), `decode_speed.c` uses two lines of inline
assembly; elsewhere it falls back to plain C.

```bash
cc -O2 -o decode_speed decode_speed.c
./decode_speed                 # about a minute
python3 k_distribution.py      # optional: rebuilds k_distribution.csv from ../games_archive (needs python-chess)
```

## What is measured

**Messages.** Each message has 20,000,000 steps.
- Each menu K_t is drawn from `k_distribution.csv`: the number of legal moves at each of the 91,863
  plies of the 1,083 games in `../games_archive`.
- Options are uniform.
- Forced steps (K = 1) write one placeholder bit (rule A).
- ASC is the code of the paper: option j < U is written 2j or 2j + 1, and the last bit carries the
  first bit of the next codeword with K ≥ 3, which is then not written. Every other option is
  written j + U.

**Settings.** Both codes are timed the same way in each.
1. One stream, menus known in advance. Every step's K, b, U and 2U are computed before timing, so
   only the reading of bits is timed.
2. One stream, each menu computed inside the timed loop from the option just decoded:
   K_{t+1} = KT[(j_t + t + 1) mod 1024], with the 1,024 values of KT drawn from the same
   distribution. This is the shape of a real domain, where the next menu depends on the last
   choice.
3. 2, 4 and 8 interleaved streams (step t goes to stream t mod S), menus known in advance. This is
   how SIMD and GPU decoders keep busy.

**Decoders.**
- Both use the same bit reader, one 8-byte load at the bit position, and the same arrays.
- Neither branches on the data, except ASC's branch for the rare passive steps (K ≤ 2, 1.6% of
  plies), which is almost always predicted right.
- TB reads b bits and keeps the codeword's first b − 1 when it is short. Its next position is
  chosen with one conditional increment after the compare. Clang otherwise emits a longer
  sequence, which made TB slower (an audit found this; see `AI_DISCLOSURE.md`).
- ASC reads b − 1 bits when a stash is pending and b bits otherwise, puts the stash back in front,
  and classifies with one compare against 2U.
- Every run is checked against the true options.

**Timing.** The median of 15 runs, divided by the number of steps.

## Results

Apple M1 (MacBook Air), Apple clang 16, `-O2`, nanoseconds per step, two runs:

| Setting | Truncated binary | ASC | TB / ASC |
|---|---|---|---|
| 1. One stream, menus known in advance | 3.85 / 3.88 | 2.49 / 2.53 | **1.54 / 1.53** |
| 2. One stream, menus from the last option | 6.11 / 6.12 | 6.81 / 6.80 | **0.90 / 0.90** |
| 3. Two streams | 1.99 / 2.01 | 1.54 / 1.56 | 1.29 / 1.29 |
| 3. Four streams | 1.13 / 1.14 | 1.47 / 1.51 | 0.77 / 0.76 |
| 3. Eight streams | 0.99 / 0.97 | 1.49 / 1.49 | 0.67 / 0.65 |

For comparison, the fixed-length code, whose widths are fixed and not just known, takes 0.68 ns per
step in setting 1. In the compiled loops, TB needs 21 instructions per step and ASC 30 (35 and 37 in
setting 2).

## What it shows

- **One stream, menus known in advance: ASC is about 1.5× faster.** In TB, the next position
  depends on the current field's bits, so each read waits for the one before. In ASC, the start of
  field t + 1 is p_t + w_t, and w_t is known before field t is read. The 4-cycle memory load then
  sits on a chain that spans two steps. The machine code gives about 12 cycles per step for TB and
  about 8 for ASC.
- **Menus from the last option: ASC is about 10% slower.** Every step now waits for "decode j_t →
  look up K_{t+1} → compute b, U and 2U → cut out field t + 1 → compare". That chain is the same for
  both codes and longer than the reading chain. ASC can still fetch field t + 1 early, but it cannot
  cut or classify it before the new menu arrives. It also does a little more work per step.
- **Four streams or more: TB is faster.** With enough streams, waiting stops mattering and the
  instruction count decides. ASC needs about 50% more instructions per step, and more state per
  stream: at eight streams it runs out of registers.
- **In chess, none of this matters.** Generating the legal moves of a position takes far longer
  than reading a few bits. The Python implementation in this repository takes 17.6 s to encode and
  decode all 91,863 plies (`roundtrip.py`), about 190 µs per ply, against a few nanoseconds for the bits.

## Not tested

- A reader that keeps the next bits in a register and refills less often. It would shorten both
  chains, and probably ASC's lead in setting 1.
- Other machines (x86, GPUs), other compilers, and real domains other than this synthetic one.

## Files

| File | What it does |
|---|---|
| `decode_speed.c` | The test: messages, encoders, decoders, timing and checks |
| `k_distribution.csv` | How often each number of legal moves occurs in `../games_archive` |
| `k_distribution.py` | Rebuilds `k_distribution.csv` from the games |
| `AI_DISCLOSURE.md` | How AI tools were used for this folder |
