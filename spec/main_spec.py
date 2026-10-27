'''
TetronOS main spec
'''

from libspec import Spec
from . import product, guardrails, milestones, packaging, constraints

class MainSpec(Spec):
    def modules(self):
        return [product, guardrails, milestones, packaging, constraints]
