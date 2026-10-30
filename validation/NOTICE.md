# Validation-source attribution

## FTN charting audit

`ftn_snapshot.py` / `ftn_contract.py` implement a repository-only source/contract
audit using the existing bounded transport, not an adapted FTN analytics model.
Source: FTN Data via nflverse, with field definitions and data terms documented by
[nflreadr at the pinned commit](https://github.com/nflverse/nflreadr/blob/23f915a5be30415aeaa0c5c80cd23b2c69cda122/R/load_ftn_charting.R).
The data and derived aggregate `docs/evidence/ftn-2024-6faae8118cc1.contract.json`
are attributed to **FTN Data via nflverse** under
[CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/).
The receipt is a modified aggregate schema/key/encoding inventory; it redistributes
no row-level data and implies no endorsement or warranty. Source CSV and pinned
documentation copies remain in the ignored local cache with retained MIT
documentation notice. This data notice does not change the project's software
license or authorize future combined exports without a separate scope review.
See `docs/FTN_CHARTING_AUDIT.md` for acquisition, rights and admission limits.

## EP feature oracle

`ep_reference.py` independently encodes the EP feature semantics documented by
nflfastR at commit `917b14e5085f352d9b00d23628759773e7d411b5` (particularly
`make_model_mutations`, `ep_model_select` and `calculate_expected_points`).
The synthetic input domain and capture validator are project-specific. Retain
the upstream notice below with reuse of this adaptation. No model binaries or
training data are included; this notice is not a license for separate datasets.

`ep_python_candidate.py` is a separate implementation of these pinned feature
semantics for an isolated parity experiment. It does not import the oracle or
reference predictions. Its dependency notices/hashes and local build/runtime
record are documented in `docs/EP_PYTHON_PARITY.md`; it is not a serving adapter.

`ep_r_capture.R` calls this pinned upstream standalone EP path and records its
actual inputs/outputs; it does not reimplement or replace its model. The raw export
retains the separately acquired fastrmodels MIT notice and DESCRIPTION alongside
the payload. See `docs/EP_R_CAPTURE.md` for the observation/replay method and limits.

Source: https://github.com/nflverse/nflfastR/blob/917b14e5085f352d9b00d23628759773e7d411b5/LICENSE.md

## MIT License

Copyright (c) 2020 Sebastian Carl; Ben Baldwin

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
