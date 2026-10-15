# AI assistance in the speed test

The paper says in one sentence that the speed test was written and reviewed with AI tools. This file
gives the details.

## The author

- Asked the question: does knowing each width before reading make decoding faster, as a blind review
  of the paper (run with Gemini) suggested for GPUs?
- Required that every code be measured the same way, with the menus (K, b, U) computed once and not
  twice, so that no code pays for work the other skips.
- Corrected Claude's first explanation of the speed-up: the check of field t does not fix where field
  t + 1 starts, but it does fix how many bits field t + 1 has, because it decides whether a stash is
  pending.
- Asked whether precomputing the menus was unfair, which led to setting 2 (each menu computed from
  the option just decoded).
- Asked for an independent audit of the code by three agents, and decided to report the test in the
  paper as a short test of this one case.

## Claude (Anthropic), in Claude Code

- Wrote `decode_speed.c` and `k_distribution.py`, ran them, and read the compiled machine code to
  explain the results.
- Proposed the multi-stream and the "menus from the last option" settings.
- Wrote `README.md` and this file.

## Three Gemini 3.8 Flash agents (Google), in Antigravity

They audited an earlier version of the code, read-only and independently:
- one checked the measurement harness (inputs, buffers, timing, checks);
- one checked the two decoders' code;
- one checked the compiled machine code.

They found one unfairness. TB updated its read position with three dependent instructions after its
compare, where one conditional increment suffices. That made TB about 13% slower than it needed to
be (4.34 instead of 3.85 ns per step), and the single-stream ratio was 1.72 instead of about 1.5. The code here has the fix (`tb_next`).
Giving ASC the same kind of change made it slower, so ASC keeps its original loop. The agents found
nothing else that favoured ASC; the only compiler artifact they noted costs ASC three instructions
per step.

## Checks

- Every timed run decodes every option of the message correctly (checked inside the program).
- `k_distribution.py` rebuilds `k_distribution.csv` from `../games_archive` with the same counts as
  the paper's figures.
- The numbers in `README.md` come from running `decode_speed.c` as it is in this folder, twice.
