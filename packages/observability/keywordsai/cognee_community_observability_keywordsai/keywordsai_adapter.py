"""
Expose `get_keywordsai_observe()` – a decorator factory that mimics Cognee's
`@observe`, but sends spans to Keywords AI using `keywordsai-tracing`.
"""

from typing import Any, Callable

from keywordsai_tracing.decorators import task, workflow
from keywordsai_tracing.main import KeywordsAITelemetry

KeywordsAITelemetry()


def get_keywordsai_observe() -> Callable[..., Any]:
    """
    Return a decorator that supports the same surface as Cognee's @observe :

      @observe                       -> Keywords AI task span
      @observe(workflow=True)        -> Keywords AI workflow span
      @observe(name="X", ...)        -> span named "X"
    """

    def observe(func: Any | None = None, **kw):  # noqa: ANN401
        def _wrap(f):
            name = kw.get("name") or kw.get("as_type") or f.__name__
            if kw.get("workflow"):
                return workflow(name=name)(f)
            return task(name=name)(f)

        return _wrap if func is None else _wrap(func)

    return observe
