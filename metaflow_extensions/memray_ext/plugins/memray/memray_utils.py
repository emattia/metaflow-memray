import time
import subprocess
import tempfile 
import os
from typing import Iterable, Dict, Any, List
from pathlib import Path

import datetime
import math
from collections import Counter
from dataclasses import asdict
from typing import Any, Dict, List, Tuple, Iterator

import memray
from memray._memray import size_fmt, compute_statistics
from memray._stats import Stats
from memray import AllocationRecord, FileReader
from memray.reporters.tui import aggregate_allocations
from memray._errors import MemrayCommandError
from memray.commands.common import warn_if_file_is_not_aggregated_and_is_too_big, warn_if_not_enough_symbols

MAX_MEMORY_RATIO = 0.95
DEFAULT_TERMINAL_LINES = 24

bin_file = "o.bin"
html_flamegraph = f"memray-flamegraph-{bin_file.split('.bin')[0]}.html"
html_table = f"memray-table-{bin_file.split('.bin')[0]}.html"

def run(step_func, tracker_kwargs):
    data = {}
    with tempfile.TemporaryDirectory() as tmp_dir:
        full_bin_path = os.path.join(tmp_dir, bin_file)
        with memray.Tracker(full_bin_path, **tracker_kwargs):
            step_func()
        # Reporter 1: flamegraph
        subprocess.run(["memray", "flamegraph", full_bin_path])
        os.rename(os.path.join(tmp_dir, html_flamegraph), html_flamegraph)
        with open(html_flamegraph, 'r') as f:
            data['flamegraph_html'] = f.read()
        os.remove(html_flamegraph)
        # Reporter 2: summary
        summary_data = get_summary_data(full_bin_path)
        data['summary_data'] = summary_data
        # Reporter 3: table
        subprocess.run(["memray", "table", full_bin_path])
        os.rename(os.path.join(tmp_dir, html_table), html_table)
        with open(html_table, 'r') as f:
            data['table_html'] = f.read()
        os.remove(html_table)
        # Reporter 4: stats
        stats_data = get_stats_data(full_bin_path)
        data['stats_data'] = stats_data
    return data

### Everything below this is copied from memray's source code ###

def _get_terminal_lines() -> int:
    try:
        return os.get_terminal_size().lines
    except OSError:
        return DEFAULT_TERMINAL_LINES

class SummaryReporter:
    KEY_TO_COLUMN_NAME = {
        1: "Total Memory",
        2: "Total Memory %",
        3: "Own Memory",
        4: "Own Memory %",
        5: "Allocation Count",
    }

    N_COLUMNS = len(KEY_TO_COLUMN_NAME)

    def __init__(self, data: Iterable[AllocationRecord], native: bool):
        snapshot = tuple(data)
        self.current_memory_size = sum(record.size for record in snapshot)
        self.total_allocations = sum(record.n_allocations for record in snapshot)
        self.snapshot_data = aggregate_allocations(
            snapshot,
            MAX_MEMORY_RATIO * self.current_memory_size,
            native,
        )

    @classmethod
    def from_snapshot(
        cls, allocations: Iterable[AllocationRecord], native: bool = False
    ) -> "SummaryReporter":
        return cls(allocations, native=native)

    def get_data(
        self,
        sort_column: int,
        *,
        max_rows: int = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        max_rows = max_rows or max(_get_terminal_lines() - 5, 10)
        
        data = []
        for location, result in self.snapshot_data.items():
            percent_total = result.total_memory / self.current_memory_size * 100
            percent_own = result.own_memory / self.current_memory_size * 100
            data.append({
                "Location": f"{location.function} at {location.file}",
                "Total Memory": result.total_memory,
                "Total Memory %": f"{percent_total:.2f}%",
                "Own Memory": result.own_memory,
                "Own Memory %": f"{percent_own:.2f}%",
                "Allocation Count": result.n_allocations
            })
        
        sort_column_name = self.KEY_TO_COLUMN_NAME[sort_column]
        
        def sort_key(x):
            value = x[sort_column_name]
            if isinstance(value, str):
                if value.endswith('%'):
                    return float(value[:-1])
                elif value.endswith('B'):  # For byte sizes
                    return value
            return value

        sorted_data = sorted(data, key=sort_key, reverse=True)[:max_rows]
        return sorted_data

def get_summary_data(
    results_path: str, 
    sort_column: int = 1, 
    max_rows: int = None, 
    temporary_allocation_threshold: int = -1
) -> Dict[str, List[Dict[str, Any]]]:
    result_path = Path(results_path)
    if not result_path.exists() or not result_path.is_file():
        raise MemrayCommandError(f"No such file: {results_path}", exit_code=1)

    try:
        reader = FileReader(os.fspath(results_path), report_progress=True)
        if reader.metadata.has_native_traces:
            warn_if_not_enough_symbols()
        if temporary_allocation_threshold < 0:
            warn_if_file_is_not_aggregated_and_is_too_big(reader, result_path)
        
        if temporary_allocation_threshold >= 0:
            snapshot = iter(
                reader.get_temporary_allocation_records(
                    threshold=temporary_allocation_threshold,
                    merge_threads=False,
                )
            )
        else:
            snapshot = iter(
                reader.get_high_watermark_allocation_records(merge_threads=True)
            )
    except OSError as e:
        raise MemrayCommandError(
            f"Failed to parse allocation records in {result_path}\nReason: {e}",
            exit_code=1,
        )

    reporter = SummaryReporter.from_snapshot(
        snapshot,
        native=reader.metadata.has_native_traces,
    )
    return reporter.get_data(sort_column=sort_column, max_rows=max_rows)


PythonStackElement = Tuple[str, str, int]

def get_histogram_databins(data: Dict[int, int], bins: int) -> List[Tuple[int, int]]:
    if bins <= 0:
        raise ValueError(f"Invalid input bins={bins}, should be greater than 0")

    low = math.log(min(filter(None, data)))
    high = math.log(max(data))
    if low == high:
        low = low / 2
    step = (high - low) / bins

    steps = [int(math.exp(low + step * (i + 1))) for i in range(bins)]
    dist: Dict[int, int] = Counter()
    for size, count in data.items():
        bucket = min(int((math.log(size) - low) // step), bins - 1) if size else 0
        dist[bucket] += count
    return [(steps[b], dist[b]) for b in range(bins)]

def describe_histogram_databins(
    databins: List[Tuple[int, int]]
) -> List[Dict[str, int]]:
    ret: List[Dict[str, int]] = []
    start = 0
    for i, (end, count) in enumerate(databins):
        adjustment = 1 if i != len(databins) - 1 else 0
        ret.append({"min_bytes": start, "max_bytes": end - adjustment, "count": count})
        start = end
    return ret

class StatsReporter:
    def __init__(self, stats: Stats, num_largest: int):
        self._stats = stats
        if num_largest < 1:
            raise ValueError(f"Invalid input num_largest={num_largest}, should be >=1")
        self.num_largest = num_largest

    def get_data(self) -> Dict[str, Any]:
        histogram_params = {
            "num_bins": 10,
            "histogram_scale_factor": 25,
        }

        alloc_size_hist = describe_histogram_databins(
            get_histogram_databins(
                self._stats.allocation_count_by_size, bins=histogram_params["num_bins"]
            )
        )

        metadata = asdict(self._stats.metadata)
        for name, val in metadata.items():
            if isinstance(val, datetime.datetime):
                metadata[name] = str(val)

        return {
            "total_num_allocations": self._stats.total_num_allocations,
            "total_bytes_allocated": self._stats.total_memory_allocated,
            "allocation_size_histogram": alloc_size_hist,
            "allocator_type_distribution": dict(
                self._get_allocator_type_distribution()
            ),
            "top_allocations_by_size": [
                {"location": self._format_location(location), "size": size}
                for location, size in self._get_top_allocations_by_size()
            ],
            "top_allocations_by_count": [
                {"location": self._format_location(location), "count": count}
                for location, count in self._get_top_allocations_by_count()
            ],
            "metadata": metadata,
        }

    @staticmethod
    def _format_location(loc: Tuple[str, str, int]) -> str:
        function, file, line = loc
        if function == "<unknown>":
            return "<stack trace unavailable>"
        return f"{function}:{file}:{line}"

    def _get_top_allocations_by_size(self) -> Iterator[Tuple[PythonStackElement, int]]:
        for location, size in self._stats.top_locations_by_size:
            yield (location, size)

    def _get_top_allocations_by_count(self) -> Iterator[Tuple[PythonStackElement, int]]:
        for location, count in self._stats.top_locations_by_count:
            yield (location, count)

    def _get_allocator_type_distribution(self) -> Iterator[Tuple[str, int]]:
        for allocator_name, count in sorted(
            self._stats.allocation_count_by_allocator.items(),
            key=lambda item: item[1],
            reverse=True,
        ):
            yield (allocator_name, count)

def get_stats_data(results_path: str, num_largest: int = 5) -> Dict[str, Any]:
    result_path = Path(results_path)
    if not result_path.exists() or not result_path.is_file():
        raise MemrayCommandError(f"No such file: {results_path}", exit_code=1)
    try:
        stats = compute_statistics(
            str(result_path),
            report_progress=True,
            num_largest=num_largest,
        )
    except OSError as e:
        raise MemrayCommandError(
            f"Failed to compute statistics for {result_path}\nReason: {e}",
            exit_code=1,
        )
    
    reporter = StatsReporter(stats, num_largest)
    return reporter.get_data()