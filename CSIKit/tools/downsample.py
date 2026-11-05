"""Downsampling for the csikit --graph views.

A capture can hold far more frames than a plot has pixels across. Drawing every
point makes each draw (and every pan, zoom or resize) slow, without showing
anything more. These helpers draw a few points per pixel column and recompute
them from the full data whenever the visible x range or the axes size changes,
so zooming in still shows every frame.

- Lines keep each pixel column's minimum and maximum, so spikes and the y range
  look the same as when every point is drawn.
- Heatmaps average the finite values of the frames in each pixel column, much as
  matplotlib's own antialiasing does when it shrinks an image to fit.

Data small enough to draw directly is drawn unchanged.
"""
import numpy as np

# Points kept per pixel column: two for lines (min and max), two image columns for heatmaps.
POINTS_PER_PIXEL = 2
MIN_PIXELS = 100


def _finite_or_nan(values) -> np.ndarray:
    values = np.asarray(values, dtype=float)
    return np.where(np.isfinite(values), values, np.nan)


def _pixel_columns(ax) -> int:
    return max(int(ax.bbox.width), MIN_PIXELS)


def _keep_alive(ax, helper):
    # Matplotlib holds callbacks through weak references, so the helper must be owned by the axes.
    if not hasattr(ax, "_csikit_downsamplers"):
        ax._csikit_downsamplers = []
    ax._csikit_downsamplers.append(helper)


def _connect(ax, callback):
    ax.callbacks.connect("xlim_changed", lambda _ax: callback())
    ax.figure.canvas.mpl_connect("resize_event", lambda _event: callback())


def minmax_indices(values: np.ndarray, start: int, stop: int, bins: int) -> np.ndarray:
    """Row indices that keep each column's envelope over rows start..stop-1.

    Rows are split into at most `bins` equal slices; each column keeps the rows of its
    minimum and maximum in every slice (NaNs are ignored), plus the first and last row.
    Returns an int array of shape (k, columns), each column in increasing order. If there
    are at most 2 * bins rows, every row is kept.
    """
    n, columns = stop - start, values.shape[1]
    if n <= 2 * bins:
        return np.broadcast_to(np.arange(start, stop)[:, None], (n, columns))

    size = -(-n // bins)
    bins = -(-n // size)
    segment = values[start:stop]
    pad = bins * size - n
    if pad:
        segment = np.concatenate([segment, np.full((pad, columns), np.nan)])
    segment = segment.reshape(bins, size, columns)

    nan = np.isnan(segment)
    low = np.argmin(np.where(nan, np.inf, segment), axis=1)
    high = np.argmax(np.where(nan, -np.inf, segment), axis=1)
    offsets = start + size * np.arange(bins)[:, None]
    picked = np.sort(np.stack([low + offsets, high + offsets], axis=1), axis=1).reshape(2 * bins, columns)

    first = np.full((1, columns), start)
    last = np.full((1, columns), stop - 1)
    return np.minimum(np.concatenate([first, picked, last]), stop - 1)


class DownsampledLines:
    """One line per column of `values` against `x`, drawn at screen resolution."""

    def __init__(self, ax, x, values, **plot_kwargs):
        self.ax = ax
        self.x = np.asarray(x, dtype=float)
        self.values = _finite_or_nan(values)
        if self.values.ndim == 1:
            self.values = self.values[:, None]

        x_shown, y_shown = self._points(0, len(self.x))
        self.lines = ax.plot(x_shown, y_shown, **plot_kwargs)
        _keep_alive(ax, self)
        _connect(ax, self.update)

    def _points(self, start, stop):
        idx = minmax_indices(self.values, start, stop, _pixel_columns(self.ax))
        return self.x[idx], np.take_along_axis(self.values, idx, axis=0)

    def _visible_rows(self):
        x0, x1 = sorted(self.ax.get_xlim())
        inside = np.flatnonzero((self.x >= x0) & (self.x <= x1))
        if not len(inside):
            return None
        # One extra point either side, so lines run to the edges of the axes.
        return max(inside[0] - 1, 0), min(inside[-1] + 2, len(self.x))

    def update(self):
        rows = self._visible_rows()
        if rows is None:
            return
        x_shown, y_shown = self._points(*rows)
        for column, line in enumerate(self.lines):
            line.set_data(x_shown[:, column], y_shown[:, column])


class DownsampledImage:
    """A heatmap of `image` (rows, frames) spread evenly over x = 0..x_max, drawn at screen resolution."""

    def __init__(self, ax, image, x_max, y_extent, **imshow_kwargs):
        self.ax = ax
        self.image = np.asarray(image)
        self.frames = self.image.shape[1]
        self.x_max = float(x_max)
        self.y_extent = tuple(y_extent)

        finite = np.isfinite(self.image)
        # Running sums let any range of frames be averaged in one step.
        self.sums = np.zeros((self.image.shape[0], self.frames + 1))
        np.cumsum(np.where(finite, self.image, 0.0), axis=1, out=self.sums[:, 1:])
        self.counts = np.zeros((self.image.shape[0], self.frames + 1))
        np.cumsum(finite, axis=1, out=self.counts[:, 1:])

        if finite.any():
            # The colour scale of the full-resolution image, not of the averages.
            imshow_kwargs.setdefault("vmin", float(self.image[finite].min()))
            imshow_kwargs.setdefault("vmax", float(self.image[finite].max()))

        shown, extent = self._columns(0, self.frames)
        self.artist = ax.imshow(shown, extent=extent, **imshow_kwargs)
        _keep_alive(ax, self)
        _connect(ax, self.update)

    def _columns(self, start, stop):
        width = self.x_max / self.frames if self.frames else 1.0
        extent = [start * width, stop * width, *self.y_extent]
        bins = POINTS_PER_PIXEL * _pixel_columns(self.ax)
        if stop - start <= bins:
            return self.image[:, start:stop], extent
        edges = np.linspace(start, stop, bins + 1).round().astype(int)
        counts = self.counts[:, edges[1:]] - self.counts[:, edges[:-1]]
        sums = self.sums[:, edges[1:]] - self.sums[:, edges[:-1]]
        with np.errstate(invalid="ignore", divide="ignore"):
            means = np.where(counts > 0, sums / counts, np.nan)
        return np.ma.masked_invalid(means), extent

    def update(self):
        if not self.frames or getattr(self, "_updating", False):
            return
        self._updating = True
        try:
            self._update()
        finally:
            self._updating = False

    def _update(self):
        width = self.x_max / self.frames
        x0, x1 = sorted(self.ax.get_xlim())
        start = int(np.clip(np.floor(x0 / width), 0, self.frames - 1)) if width else 0
        stop = int(np.clip(np.ceil(x1 / width), start + 1, self.frames)) if width else self.frames
        shown, extent = self._columns(start, stop)
        self.artist.set_data(shown)
        self.artist.set_extent(extent)
        # set_extent rescales the axes to the image; keep the user's view.
        self.ax.set_xlim(x0, x1, emit=False)
