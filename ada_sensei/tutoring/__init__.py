"""Context-aware tutoring: context assembly and next-action recommendations.

Spec 0011 implementation. This package is application logic shared by the
orchestrator (``TeacherAgent``) and the presentation layer (``CommandRouter``
helpers): it assembles evidence-grounded context and derives at most one
validated, optional recommendation. It never executes actions, never mutates
stage or mastery state, and never invents student facts — missing information
stays ``None``/``unknown``.
"""

from .context import TutorContext, assemble_context
from .models import Recommendation
from .recommender import recommend_next

__all__ = ["Recommendation", "TutorContext", "assemble_context", "recommend_next"]
