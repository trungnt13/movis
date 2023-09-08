from __future__ import annotations

from typing import Hashable, Protocol

import numpy as np


class Layer(Protocol):
    """The protocol that defimes the minimal interface for a layer."""

    def __call__(self, time: float) -> np.ndarray | None:
        """The minimum required method to implement a layer. All layers must implement it.

        Specifically, this method returns a ``numpy.ndarray`` of shape ``(H, W, 4)`` with RGBA order and dtype as
        ``numpy.uint8``, or ``None``, given a time.
        When a ``numpy.ndarray`` is returned, Movis considers this array as an image and uses it as one of the layers
        for rendering the video. If ``None`` is returned, Movis does not render its layer.

        Args:
            time: A scalar variable representing time.

        Returns:
            ``None`` if nothing is to be rendered, otherwise ``numpy.ndarray``.
        """
        raise NotImplementedError


class BasicLayer(Layer):
    """The protocol that defines the basic interface for a layer with some optional properties."""

    @property
    def duration(self) -> float:
        """An optional but desirable property for any layer implementation.

        This property should return the duration for which the layer will persist.
        If not implemented, it is assumed that the layer has an indefinitely large duration.

        Returns:
            The duration for which the layer will persist.
        """
        return 1e6

    def get_key(self, time: float) -> Hashable:
        """An optional but desirable method for any layer implementation.

        This method returns a hashable value representing the 'state' of the layer at a given time.
        If the keys are the same, the array returned by this layer must also be identical.
        It is used for caching compositions, and in the case of videos where static frames persist,
        Movis will use the cache to accelerate video rendering.

        If not implemented, Movis assumes that the layer is independent at each time frame,
        `i.e.`, it will not use cache-based rendering.

        Returns:
            A hashable key that represents the state of the layer at the given time.
        """
        return time