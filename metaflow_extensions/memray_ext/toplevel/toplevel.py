__mf_extensions__ = "memray-ext"

# Make the switch decorator available at the top level.
from ..plugins.memray import memray_deco as memray

import pkg_resources

try:
    __version__ = pkg_resources.get_distribution("metaflow-memray").version
except:
    # this happens on remote environments since the job package
    # does not have a version
    __version__ = None