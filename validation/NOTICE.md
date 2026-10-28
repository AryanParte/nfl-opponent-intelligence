# Upstream attribution for the EP feature oracle

`ep_reference.py` independently encodes the EP feature semantics documented by
nflfastR at commit `917b14e5085f352d9b00d23628759773e7d411b5` (particularly
`make_model_mutations`, `ep_model_select` and `calculate_expected_points`).
The synthetic input domain and capture validator are project-specific. Retain
the upstream notice below with reuse of this adaptation. No model binaries or
training data are included; this notice is not a license for separate datasets.

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
