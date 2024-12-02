from metaflow.cards import MetaflowCard
from metaflow.exception import MetaflowException

class MemrayFlamegraphCard(MetaflowCard):

    type = "memray_flamegraph"

    def render(self, task):
        return task.data.flamegraph_html
        
class MemrayTableCard(MetaflowCard):

    type = "memray_table"

    def render(self, task):
        return task.data.table_html

class MemrayAllocatorCard(MetaflowCard):

    type = "memray_allocator"

    def render(self, task):
        from .utils import create_stats_histogram_html
        return create_stats_histogram_html(task.data.stats_data['allocation_size_histogram'])


CARDS = [MemrayFlamegraphCard, MemrayTableCard, MemrayAllocatorCard]