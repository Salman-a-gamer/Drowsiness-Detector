"""One scare per closure, with a cooldown and open-eye rearming."""
class ScareGate:
    def __init__(self, cooldown=20.0):
        self.cooldown = cooldown
        self.active = False
        self.armed = False
        self.until = 0.0

    def observe(self, eyes_open):
        if eyes_open is True and not self.active:
            self.armed = True

    def request(self, now):
        if self.active or not self.armed or now < self.until:
            return False
        self.armed = False
        self.active = True
        return True

    def finish(self, now):
        self.active = False
        self.until = now + self.cooldown

    def reset(self):
        self.active = self.armed = False
        self.until = 0.0
