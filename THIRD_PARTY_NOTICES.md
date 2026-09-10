# Third-party notices

Protocol constants and implementation ideas are derived from the following
MIT-licensed projects. Their copyright and permission notices are reproduced
to preserve attribution.

## Switch2BTLink

MIT License

Copyright (c) 2026 KumuIi

Based on protocol research from the joycon2py and joycon2cpp projects (MIT License,
Copyright (c) TheFrano and contributors) and BLE reverse engineering by german77.

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

## Architecture and protocol research references

The following projects were consulted to compare virtual-controller and
haptics architectures. No source code from these projects is incorporated in
this MIT-licensed distribution.

- XinHeLianSheng Pro2 Bridge by LeonChrome (Apache License 2.0):
  https://github.com/LeonChrome/XinHeLianSheng-Pro2-Bridge
- S2P-XInput-Lite by duoduo-88 (GNU General Public License v3.0):
  https://github.com/duoduo-88/S2P-XInput-Lite

## VIIPER Haptic v0.8.0 optional runtime

The packaged application contains `viiper-haptic.exe` from the
`codex/v6.2.32-stick-calibration-test` branch of XinHeLianSheng Pro2 Bridge.
It is launched as a separate process only when Nintendo output mode is chosen;
the MIT-licensed bridge communicates with it through VIIPER's documented local
TCP API. VIIPER is licensed under GNU GPL version 3. The complete license is
distributed as `runtime/VIIPER_LICENSE.txt` and copied beside packaged builds.

- Upstream source: https://github.com/Alia5/VIIPER
- Exact redistributed source tree:
  https://github.com/LeonChrome/XinHeLianSheng-Pro2-Bridge/tree/codex/v6.2.32-stick-calibration-test/tools/viiper/haptic-src
- Runtime SHA-256:
  `F153400F095817AF5056A6658A6EBD93A46F533F0BCD5E5DB3E59B0731278727`

## joycon2cpp

MIT License

Copyright (c) 2025 Frano

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
