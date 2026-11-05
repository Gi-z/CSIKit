import os

# Must happen before anything imports matplotlib.pyplot, so plt.show() never blocks.
os.environ.setdefault("MPLBACKEND", "Agg")

import pytest  # noqa: E402


def pytest_addoption(parser):
    parser.addoption(
        "--runslow", action="store_true", default=False,
        help="also run tests marked 'slow' (they parse the largest sample captures)",
    )
    parser.addoption(
        "--update-snapshots", action="store_true", default=False,
        help="rewrite golden reader snapshots from the current output instead of comparing",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--runslow"):
        return
    skip_slow = pytest.mark.skip(reason="slow test: run with --runslow")
    for item in items:
        if "slow" in item.keywords:
            item.add_marker(skip_slow)


@pytest.fixture
def update_snapshots(request):
    return request.config.getoption("--update-snapshots")
