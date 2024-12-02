from metaflow.decorators import StepDecorator
from metaflow.exception import MetaflowException
from collections import defaultdict
import json


class MemrayStepDecorator(StepDecorator):

    name = "_memray"

    defaults = dict(
        native_traces=False,
        trace_python_allocators=False,
        follow_fork=False,
        memory_interval_ms=10,
    )

    def task_decorate(
        self, step_func, flow, graph, retry_count, max_user_code_retries, ubf_context
    ):
        from functools import partial
        from .memray_utils import run as memray_run

        def wrapper(*args, **kwargs):
            results = memray_run(
                step_func,
                {
                    "native_traces": self.attributes['native_traces'],
                    "trace_python_allocators": self.attributes['trace_python_allocators'],
                    "follow_fork": self.attributes['follow_fork'],
                    "memory_interval_ms": self.attributes['memory_interval_ms']
                },
            )
            for k, v in results.items():
                setattr(flow, k, v)
            
        return partial(wrapper, step_func=step_func)