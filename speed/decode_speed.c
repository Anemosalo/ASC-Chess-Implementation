// decode_speed.c: how fast do the decoders of truncated binary (TB) and ASC read a message?
//
// A short test, not a study of decoder engineering: synthetic messages, hand-written decoders, one
// machine. See README.md for the setup and the results, and AI_DISCLOSURE.md for how it was made.
//
//   cc -O2 -o decode_speed decode_speed.c && ./decode_speed
//
// Messages: N steps. Menus K_t are drawn from k_distribution.csv (the K of every ply of the 1,083
// games in ../games_archive), options j_t are uniform, and forced steps (K = 1) write one
// placeholder bit (rule A). ASC is the code of the paper: option j < U is written 2j or 2j+1 (its
// last bit carries the first bit of the next codeword with K >= 3, which is then not written), any
// other option j + U.
//
// Three settings, all timed the same way for both codes:
//   1. one stream, menus known in advance: every step's (K, b, U, 2U) is computed before timing;
//   2. one stream, each menu computed inside the loop from the option just decoded:
//      K_{t+1} = KT[(j_t + t + 1) mod 1024], with KT drawn from the same distribution;
//   3. S = 2, 4, 8 interleaved streams (step t in stream t mod S), menus known in advance.
// Both decoders use the same bit reader (one 8-byte load at the bit position), the same arrays and
// no data-dependent branches, except ASC's branch for the rare passive steps (K <= 2). Every run
// is checked against the true options.
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define N 20000000
#define RUNS 15
#define MAXS 8

static uint8_t K[N], B[N], U[N], U2[N], J[N], OUT[N], C[N];
static uint16_t KT[1024];
static const uint8_t *BUFS[MAXS];

// ------------------------------------------------------------------ helpers
static uint64_t rng = 88172645463325252ULL;
static uint64_t next(void) { rng ^= rng << 13; rng ^= rng >> 7; rng ^= rng << 17; return rng; }

static inline uint64_t peek(const uint8_t *buf, uint64_t pos, unsigned n) {  // 1 <= n <= 57
  uint64_t w;
  memcpy(&w, buf + (pos >> 3), 8);
  w = __builtin_bswap64(w);
  return (w << (pos & 7)) >> (64 - n);
}

typedef struct { uint8_t *buf; uint64_t pos; } Writer;
static void put(Writer *w, uint32_t v, unsigned n) {
  for (int i = n - 1; i >= 0; i--) {
    if ((v >> i) & 1) w->buf[w->pos >> 3] |= 0x80 >> (w->pos & 7);
    w->pos++;
  }
}

static void menu_of(unsigned k, unsigned *b, unsigned *u) {  // rule A: K = 1 reads one bit, U = 0
  unsigned bb = 0;
  while ((1u << bb) < k) bb++;
  if (k == 1) bb = 1;
  *b = bb;
  *u = k == 1 ? 0 : (1u << bb) - k;
}

// ------------------------------------------------------------------ messages
static int nk;
static int ks[256];
static long ws[256], total;

static void load_distribution(const char *csv) {
  FILE *f = fopen(csv, "r");
  if (!f) { perror(csv); exit(1); }
  char line[128];
  if (!fgets(line, sizeof line, f)) exit(1);  // header
  while (nk < 256 && fgets(line, sizeof line, f))
    if (sscanf(line, "%d,%ld", &ks[nk], &ws[nk]) == 2) total += ws[nk++];
  fclose(f);
}
static unsigned draw_k(void) {
  long r = next() % total;
  for (int i = 0; i < nk; i++) { if (r < ws[i]) return ks[i]; r -= ws[i]; }
  return ks[nk - 1];
}
static void set_step(int t, unsigned k) {
  unsigned b, u;
  menu_of(k, &b, &u);
  K[t] = k; B[t] = b; U[t] = u; U2[t] = 2 * u; J[t] = next() % k;
}
static void messages_independent(void) {  // settings 1 and 3
  for (int t = 0; t < N; t++) set_step(t, draw_k());
}
static void messages_from_last_option(void) {  // setting 2
  for (int i = 0; i < 1024; i++) KT[i] = draw_k();
  unsigned k = KT[0];
  for (int t = 0; t < N; t++) { set_step(t, k); k = KT[(J[t] + t + 1) & 1023]; }
}

// ------------------------------------------------------------------ encoders (not timed)
// Each encodes the steps off, off + stride, ... as one stream.
static void enc_naive(uint8_t *buf) {
  Writer w = {buf, 0};
  for (int t = 0; t < N; t++) put(&w, J[t], B[t]);
}
static void enc_tb(uint8_t *buf, int off, int stride) {
  Writer w = {buf, 0};
  for (int t = off; t < N; t += stride) {
    if (J[t] < U[t]) put(&w, J[t], B[t] - 1);
    else put(&w, J[t] + U[t], B[t]);
  }
}
static void enc_asc(uint8_t *buf, int off, int stride) {
  unsigned next_msb = 0;  // first bit of the next stash-capable codeword (0 after the last one)
  int last = off + (N - 1 - off) / stride * stride;
  for (int t = last; t >= off; t -= stride) {
    if (K[t] <= 2) continue;
    unsigned c = J[t] < U[t] ? 2u * J[t] + next_msb : J[t] + U[t];
    C[t] = c;
    next_msb = c >> (B[t] - 1);
  }
  Writer w = {buf, 0};
  int pend = 0;
  for (int t = off; t < N; t += stride) {
    if (K[t] <= 2) { put(&w, K[t] == 2 ? J[t] : 0, 1); continue; }
    put(&w, C[t] & ((1u << (B[t] - pend)) - 1), B[t] - pend);
    pend = J[t] < U[t];
  }
}

// ------------------------------------------------------------------ decoders (timed)
// TB: read b bits x; the codeword is short iff x < 2U; then j = x >> 1, else j = x - U. The next
// position is pos + b - 1 or pos + b, chosen with one conditional increment after the compare
// (forced on AArch64, where clang otherwise emits a longer set/subtract/add sequence).
static inline uint64_t tb_next(uint64_t pos, unsigned b, unsigned x, unsigned u2) {
  uint64_t p1 = pos + b - 1;
#if defined(__aarch64__)
  uint64_t np;
  __asm__("cmp %w[x], %w[u2]\n\tcsinc %[np], %[p1], %[p1], lo"
          : [np] "=r"(np) : [x] "r"(x), [u2] "r"(u2), [p1] "r"(p1) : "cc");
  return np;
#else
  return x < u2 ? p1 : p1 + 1;
#endif
}
#define TB_STEP(i, buf, pos) do { unsigned b_ = B[i], u2_ = U2[i]; \
    unsigned x_ = peek(buf, pos, b_), m_ = 0u - (x_ < u2_); \
    OUT[i] = ((x_ >> 1) & m_) | ((x_ - U[i]) & ~m_); pos = tb_next(pos, b_, x_, u2_); } while (0)

// ASC: a pending stash is kept already masked (sig = aliasable & c, 0 when none is pending). Read
// w = b - pe bits, put the stash back in front, classify with one compare against 2U.
#define ASC_STEP(i, buf, pos, pe, sig) do { \
    if (__builtin_expect(K[i] <= 2, 0)) { OUT[i] = peek(buf, pos, 1); pos += 1; } \
    else { unsigned b_ = B[i], w_ = b_ - pe; unsigned r_ = peek(buf, pos, w_); pos += w_; \
      unsigned c_ = r_ | (sig << (b_ - 1)), a_ = c_ < U2[i], m_ = 0u - a_; \
      OUT[i] = ((c_ >> 1) & m_) | ((c_ - U[i]) & ~m_); sig = a_ & c_; pe = a_; } } while (0)

static void naive_1(void) {
  const uint8_t *f = BUFS[0];
  uint64_t p = 0;
  for (int t = 0; t < N; t++) { OUT[t] = peek(f, p, B[t]); p += B[t]; }
}
static void tb_1(void) {
  const uint8_t *f0 = BUFS[0]; uint64_t p0 = 0;
  for (int t = 0; t < N; t++) TB_STEP(t, f0, p0);
}
static void asc_1(void) {
  const uint8_t *f0 = BUFS[0]; uint64_t p0 = 0; unsigned e0 = 0, g0 = 0;
  for (int t = 0; t < N; t++) ASC_STEP(t, f0, p0, e0, g0);
}
static void tb_2(void) {
  const uint8_t *f0 = BUFS[0], *f1 = BUFS[1]; uint64_t p0 = 0, p1 = 0;
  for (int t = 0; t + 2 <= N; t += 2) { TB_STEP(t, f0, p0); TB_STEP(t + 1, f1, p1); }
}
static void asc_2(void) {
  const uint8_t *f0 = BUFS[0], *f1 = BUFS[1]; uint64_t p0 = 0, p1 = 0;
  unsigned e0 = 0, g0 = 0, e1 = 0, g1 = 0;
  for (int t = 0; t + 2 <= N; t += 2) { ASC_STEP(t, f0, p0, e0, g0); ASC_STEP(t + 1, f1, p1, e1, g1); }
}
static void tb_4(void) {
  const uint8_t *f0 = BUFS[0], *f1 = BUFS[1], *f2 = BUFS[2], *f3 = BUFS[3];
  uint64_t p0 = 0, p1 = 0, p2 = 0, p3 = 0;
  for (int t = 0; t + 4 <= N; t += 4) {
    TB_STEP(t, f0, p0); TB_STEP(t + 1, f1, p1); TB_STEP(t + 2, f2, p2); TB_STEP(t + 3, f3, p3);
  }
}
static void asc_4(void) {
  const uint8_t *f0 = BUFS[0], *f1 = BUFS[1], *f2 = BUFS[2], *f3 = BUFS[3];
  uint64_t p0 = 0, p1 = 0, p2 = 0, p3 = 0;
  unsigned e0 = 0, g0 = 0, e1 = 0, g1 = 0, e2 = 0, g2 = 0, e3 = 0, g3 = 0;
  for (int t = 0; t + 4 <= N; t += 4) {
    ASC_STEP(t, f0, p0, e0, g0); ASC_STEP(t + 1, f1, p1, e1, g1);
    ASC_STEP(t + 2, f2, p2, e2, g2); ASC_STEP(t + 3, f3, p3, e3, g3);
  }
}
static void tb_8(void) {
  const uint8_t *f0 = BUFS[0], *f1 = BUFS[1], *f2 = BUFS[2], *f3 = BUFS[3];
  const uint8_t *f4 = BUFS[4], *f5 = BUFS[5], *f6 = BUFS[6], *f7 = BUFS[7];
  uint64_t p0 = 0, p1 = 0, p2 = 0, p3 = 0, p4 = 0, p5 = 0, p6 = 0, p7 = 0;
  for (int t = 0; t + 8 <= N; t += 8) {
    TB_STEP(t, f0, p0); TB_STEP(t + 1, f1, p1); TB_STEP(t + 2, f2, p2); TB_STEP(t + 3, f3, p3);
    TB_STEP(t + 4, f4, p4); TB_STEP(t + 5, f5, p5); TB_STEP(t + 6, f6, p6); TB_STEP(t + 7, f7, p7);
  }
}
static void asc_8(void) {
  const uint8_t *f0 = BUFS[0], *f1 = BUFS[1], *f2 = BUFS[2], *f3 = BUFS[3];
  const uint8_t *f4 = BUFS[4], *f5 = BUFS[5], *f6 = BUFS[6], *f7 = BUFS[7];
  uint64_t p0 = 0, p1 = 0, p2 = 0, p3 = 0, p4 = 0, p5 = 0, p6 = 0, p7 = 0;
  unsigned e0 = 0, g0 = 0, e1 = 0, g1 = 0, e2 = 0, g2 = 0, e3 = 0, g3 = 0;
  unsigned e4 = 0, g4 = 0, e5 = 0, g5 = 0, e6 = 0, g6 = 0, e7 = 0, g7 = 0;
  for (int t = 0; t + 8 <= N; t += 8) {
    ASC_STEP(t, f0, p0, e0, g0); ASC_STEP(t + 1, f1, p1, e1, g1);
    ASC_STEP(t + 2, f2, p2, e2, g2); ASC_STEP(t + 3, f3, p3, e3, g3);
    ASC_STEP(t + 4, f4, p4, e4, g4); ASC_STEP(t + 5, f5, p5, e5, g5);
    ASC_STEP(t + 6, f6, p6, e6, g6); ASC_STEP(t + 7, f7, p7, e7, g7);
  }
}

// Setting 2: each menu is computed inside the loop from the option just decoded, the same way for
// both codes (b = ceil(log2 K) with a count of leading zeros, U = 2^b - K, U = 0 for K = 1).
static inline void menu_fast(unsigned k, unsigned *b, unsigned *u) {
  unsigned bb = 32 - __builtin_clz((k - 1) | 1);
  *b = bb;
  *u = ((1u << bb) - k) & (0u - (k > 1));
}
static void tb_from_last(void) {
  const uint8_t *f = BUFS[0];
  uint64_t pos = 0;
  unsigned k = KT[0];
  for (int t = 0; t < N; t++) {
    unsigned b, u;
    menu_fast(k, &b, &u);
    unsigned x = peek(f, pos, b), m = 0u - (x < 2 * u);
    unsigned j = ((x >> 1) & m) | ((x - u) & ~m);
    pos = tb_next(pos, b, x, 2 * u);
    OUT[t] = j;
    k = KT[(j + t + 1) & 1023];
  }
}
static void asc_from_last(void) {
  const uint8_t *f = BUFS[0];
  uint64_t pos = 0;
  unsigned k = KT[0], pe = 0, sig = 0;
  for (int t = 0; t < N; t++) {
    unsigned b, u, j;
    menu_fast(k, &b, &u);
    if (__builtin_expect(k <= 2, 0)) { j = peek(f, pos, 1); pos += 1; }
    else {
      unsigned w = b - pe, r = peek(f, pos, w);
      pos += w;
      unsigned c = r | (sig << (b - 1)), a = c < 2 * u, m = 0u - a;
      j = ((c >> 1) & m) | ((c - u) & ~m);
      sig = a & c;
      pe = a;
    }
    OUT[t] = j;
    k = KT[(j + t + 1) & 1023];
  }
}

// ------------------------------------------------------------------ timing
static double now(void) {
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC_RAW, &ts);
  return ts.tv_sec + ts.tv_nsec * 1e-9;
}
static int cmp_d(const void *a, const void *b) {
  double x = *(const double *)a, y = *(const double *)b;
  return (x > y) - (x < y);
}
static double timeit(void (*f)(void), const char *name) {  // median ns per step over RUNS runs
  double ts[RUNS];
  for (int r = 0; r < RUNS; r++) {
    double t0 = now();
    f();
    ts[r] = now() - t0;
    if (memcmp(OUT, J, N)) { fprintf(stderr, "%s: decoded options differ\n", name); exit(1); }
  }
  qsort(ts, RUNS, sizeof ts[0], cmp_d);
  return ts[RUNS / 2] / N * 1e9;
}

static size_t BYTES = N + 64;  // at most 8 bits per step, plus room for the 8-byte peek
static uint8_t *stream_buf[2][MAXS];
static void encode_streams(int code, int S) {  // code 0 = TB, 1 = ASC
  for (int k = 0; k < S; k++) {
    if (!stream_buf[code][k]) stream_buf[code][k] = malloc(BYTES);
    memset(stream_buf[code][k], 0, BYTES);
    if (code) enc_asc(stream_buf[code][k], k, S); else enc_tb(stream_buf[code][k], k, S);
    BUFS[k] = stream_buf[code][k];
  }
}

int main(int argc, char **argv) {
  load_distribution(argc > 1 ? argv[1] : "k_distribution.csv");
  printf("%d steps per message, median of %d runs, ns per step\n\n", N, RUNS);

  messages_independent();
  printf("1. One stream, menus known in advance\n");
  uint8_t *nb = calloc(BYTES, 1);
  enc_naive(nb);
  BUFS[0] = nb;
  printf("   fixed-length code   %6.3f\n", timeit(naive_1, "fixed-length"));
  encode_streams(0, 1);
  double t1 = timeit(tb_1, "TB");
  encode_streams(1, 1);
  double a1 = timeit(asc_1, "ASC");
  printf("   truncated binary    %6.3f\n   ASC                 %6.3f   (TB / ASC = %.2f)\n\n", t1, a1, t1 / a1);

  printf("3. Interleaved streams, menus known in advance\n   streams                 1       2       4       8\n");
  void (*tbs[4])(void) = {tb_1, tb_2, tb_4, tb_8}, (*ascs[4])(void) = {asc_1, asc_2, asc_4, asc_8};
  int Ss[4] = {1, 2, 4, 8};
  double res[2][4];
  for (int q = 0; q < 4; q++) {
    encode_streams(0, Ss[q]); res[0][q] = timeit(tbs[q], "TB streams");
    encode_streams(1, Ss[q]); res[1][q] = timeit(ascs[q], "ASC streams");
  }
  printf("   truncated binary  ");
  for (int q = 0; q < 4; q++) printf(" %6.3f", res[0][q]);
  printf("\n   ASC               ");
  for (int q = 0; q < 4; q++) printf(" %6.3f", res[1][q]);
  printf("\n   TB / ASC          ");
  for (int q = 0; q < 4; q++) printf(" %6.2f", res[0][q] / res[1][q]);
  printf("\n\n");

  messages_from_last_option();
  printf("2. One stream, each menu computed from the option just decoded\n");
  encode_streams(0, 1);
  double t2 = timeit(tb_from_last, "TB, menus from the last option");
  encode_streams(1, 1);
  double a2 = timeit(asc_from_last, "ASC, menus from the last option");
  printf("   truncated binary    %6.3f\n   ASC                 %6.3f   (TB / ASC = %.2f)\n", t2, a2, t2 / a2);
  return 0;
}
