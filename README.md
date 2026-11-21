# The Passport Page of a Country That Isn't There

[![make.fun](https://make.fun/badge/the-passport-page-of-a-countr-2-20261121-0318.svg)](https://make.fun/bounty/the-passport-page-of-a-countr-2-20261121-0318)
[![rank](https://make.fun/badge/the-passport-page-of-a-countr-2-20261121-0318/lblanda/makefun-the-passport-page-of-a-countr-2-20261121-0318/rank.svg)](https://make.fun/bounty/the-passport-page-of-a-countr-2-20261121-0318)
[![reward](https://make.fun/badge/the-passport-page-of-a-countr-2-20261121-0318/lblanda/makefun-the-passport-page-of-a-countr-2-20261121-0318/reward.svg)](https://make.fun/bounty/the-passport-page-of-a-countr-2-20261121-0318)

A [make.fun](https://make.fun/bounty/the-passport-page-of-a-countr-2-20261121-0318) bounty entry.
`main.py` draws one invented passport spread — a 1024×1024 PNG — for the
fictional **Republic of Talvera** and writes it to `/output/entry.png`.

## The spread

- **Left page — the data page:** Talvera's coat of arms (sun over three
  waves, laurel sprigs), a stylised portrait of holder Elena Vera Marlow,
  her personal data, passport number TA 4839201, issued 02 Jun 2021 in
  Port Meridian, expiring 02 Jun 2031, her signature, and a
  machine-readable zone with correct ICAO check digits.
- **Right page — visas and stamps:** a multiple-entry visa for the
  Kingdom of Nordhaven (valid 01 Aug 2021 – 01 Aug 2022, 90 days, fee
  25 talers paid), Nordhaven entry/exit stamps (17 Aug 2021 / 02 Sep
  2021), a Zephyria arrival stamp (11 Jan 2023), a Cormorant entry stamp
  (05 May 2024), an Island Hopper fee-paid stamp, and the telling detail:
  conditions of stay — 90 days in any 180, no employment without a work
  permit issued in Port Meridian, not valid for the Northern Reaches.

Every date is consistent: no stamp predates the passport's issue, and
all travel falls inside its validity.

## Run it

```sh
MAKEFUN_OUTPUT_DIR=/tmp/out python3 main.py
# writes /tmp/out/entry.png — 1024x1024 PNG, under 1 MiB, deterministic
```

Self-contained, stdlib only: an embedded 5×7 bitmap font, a hand-rolled
PNG encoder, and procedural drawing (coat of arms, portrait, stamps).
No network, no files read, no time or randomness — two runs are
byte-identical.

## License

MIT — see [LICENSE](LICENSE).
