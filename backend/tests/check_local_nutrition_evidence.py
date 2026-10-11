"""Explicit local evidence integration: offline runner pattern check_local_nutrition_evidence.py.

Requires the private reviewed manifest/artifact bundle; absence is a failure, not a skip.
Reuses all regression assertions against real artifact pins but only synthetic SQLite DBs.
"""
from contextlib import nullcontext

import test_nutrition_activation as activation_tests
import test_nutrition_g4_correction as correction_tests


class LocalActivationEvidenceTests(activation_tests.ActivationTests):
    def evidence_context(self):
        return nullcontext()


class LocalG4EvidenceTests(correction_tests.G4CorrectionTests):
    def evidence_context(self):
        return nullcontext()
