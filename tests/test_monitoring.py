import unittest
from drowsy_guard.monitoring import ScareGate

class GateTests(unittest.TestCase):
    def test_one_scare_and_reopen_after_cooldown(self):
        gate = ScareGate(20)
        self.assertFalse(gate.request(0))
        gate.observe(True)
        self.assertTrue(gate.request(1))
        self.assertFalse(gate.request(2))
        gate.finish(3)
        gate.observe(None)
        self.assertFalse(gate.request(25))
        gate.observe(True)
        self.assertFalse(gate.request(10))
        self.assertTrue(gate.request(25))

    def test_stop_clears_pending_and_requires_open_eyes(self):
        gate = ScareGate()
        gate.observe(True)
        gate.request(0)
        gate.reset()
        self.assertFalse(gate.active)
        self.assertFalse(gate.request(20))
