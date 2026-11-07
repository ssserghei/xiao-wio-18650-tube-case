# TODO

Changes planned after the first test print. See also *Things to check on the first print* in the [README](README.md).

## Bayonet that a coarse printer can make

**Problem.** The helical bayonet works, but its slots are about 1 mm deep in a 1.5 mm sleeve wall. That leaves roughly 0.8 mm of wall over each slot, and the lugs are only 1 mm thick. A coarse FDM printer prints this badly.

**Plan.**

- **Drop the O-ring.** The seal is illusory: printed PETG is porous, so a rubber ring does not make the case tight. Remove the groove (`ORingGrooveStartZ` / `ORingGrooveWidth`, Z = 2.4–4.4 mm on the rear wall) and update the "sealing" decisions in `docs/design-log-ru.md`.
- **Use the freed rear wall for a stronger bayonet.** Z = 0–4.9 mm becomes available for it:
  - lugs about 2–2.5 mm thick instead of 1 mm, wide enough to keep the bearing area;
  - shallower slots, so the sleeve keeps at least 1 mm of wall over them;
  - generous clearances, 0.3–0.4 mm instead of 0.05–0.1, and a coarser lead that still tightens at the end of the turn;
  - fewer, larger features if that prints more reliably, for example two lugs instead of three.
- **Check after the change:** the antenna wall (`WireChannelStartZ` = 4.9 mm, `antenna_free_thread` ≥ 3.5 mm) must not change, and `check_stage_29_32.py` must still pass the bayonet travel test.

## Other open items

- Re-slice the sleeve with *Seam position: Rear* for a straight seam instead of a spiral.
- Add photos of the printed and assembled case to the README.
