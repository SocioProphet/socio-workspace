"""Root pytest config: put the vendored kernel (third_party/) on sys.path.

The reasoned responder consumes the vendored `procyber.semantic` kernel from
`third_party/`. Adding that directory here lets tests import it the same way the
runtime does, so the cross-repo integration test exercises the real vendored code.
"""

import os
import sys

_VENDOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "third_party")
if _VENDOR not in sys.path:
    sys.path.insert(0, _VENDOR)
