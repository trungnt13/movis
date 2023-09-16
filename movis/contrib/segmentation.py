from __future__ import annotations

import hashlib
import sys
import urllib.request
from pathlib import Path

import numpy as np


class RobustVideoMatting:
    """Extract the foreground using the RobustVideoMatting [Li2021].

    This effect uses a deep learning model to automatically identify the area of persons in a given frame
    and extract it as the foreground. Note that while there is no need to set up greenbacks or
    other special imaging environments, the quality is not at the production level.
    This effect is useful in areas that generally do not require foreground extraction quality,
    such as explainer videos.

    Args:
        onnx_file:
            The path to the ONNX file of the model. Download it from https://github.com/PeterL1n/RobustVideoMatting
            and put it in an appropriate location. If None, the default model will be downloaded
            and chached in ``~/.cache/movis``. The default model is ``rvm_mobilenetv3_fp16.onnx``.
        downsample_ratio:
            The downsample ratio to accelerate the inference speed. The default value is 0.25.
        recurrent_state:
            The flag to indicate whether the model uses a reccurent state.
            Enabling this flag tends to improve quality, but may also produce unstable results in some cases.
            The default value is ``True``.
    """

    default_model_url = \
        'https://github.com/PeterL1n/RobustVideoMatting/releases/download/v1.0.0/rvm_mobilenetv3_fp16.onnx'
    default_md5_digest = 'f8c8ae3ed12f3d6ba09211b58a406a28'

    def __init__(
            self, onnx_file: str | Path | None = None, downsample_ratio: float = 0.25,
            recurrent_state: bool = True):
        import onnxruntime
        self._downsample_ratio = np.array([downsample_ratio], dtype=np.float32)
        assert onnx_file is None or isinstance(onnx_file, (str, Path))
        self._onnx_file = onnx_file
        self._session: onnxruntime.InferenceSession | None = None
        self._state: list[np.ndarray] = [np.zeros([1, 1, 1, 1], dtype=np.float16)] * 4
        self._recurrent_state = recurrent_state

    @property
    def recurrent_state(self) -> bool:
        """Whether the model uses a recurrent state."""
        return self._recurrent_state

    def get_key(self, time: float) -> float:
        """Return the key for caching."""
        if self._recurrent_state:
            return time
        else:
            return -1.0

    def __call__(self, prev_frame: np.ndarray, time: float) -> np.ndarray:
        import onnxruntime
        if self._session is None:
            if self._onnx_file is None:
                self._onnx_file = _download_and_cache(self.default_model_url, self.default_md5_digest)
            else:
                self._onnx_file = Path(self._onnx_file)
            self._session = onnxruntime.InferenceSession(str(self._onnx_file))

        img = prev_frame[:, :, :3].transpose(2, 0, 1)[None, :, :, :]
        img = img.astype(np.float16) / 255
        s0 = self._state
        _, alpha, s10, s11, s12, s13 = self._session.run([], {
            'src': img,
            'r1i': s0[0], 'r2i': s0[1], 'r3i': s0[2], 'r4i': s0[3],
            'downsample_ratio': self._downsample_ratio,
        })
        if self._recurrent_state:
            self._state = [s10, s11, s12, s13]
        alpha = np.clip(alpha * 255, 0, 255).astype(np.uint8)[0].transpose(1, 2, 0)
        dst = np.concatenate([prev_frame[:, :, :3], alpha], axis=2)
        return dst


def _download_and_cache(url, expected_md5: str | None = None) -> Path:
    filename = Path(url).name
    home_dir = Path.home()
    cache_dir = home_dir / ".cache" / "movis"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / filename
    if cache_path.exists():
        actual_md5 = _calculate_md5(cache_path)
        if expected_md5 is None or actual_md5 == expected_md5:
            return cache_path
        else:
            sys.stderr.write(f"MD5 mismatch: expected {expected_md5}, got {actual_md5}.")
            sys.stderr.flush()

    sys.stderr.write(f'Downloading {filename} from {url}...\n')
    sys.stderr.flush()
    urllib.request.urlretrieve(url, cache_path)
    return cache_path


def _calculate_md5(file_path: Path) -> str:
    """Calculate the MD5 hash of a file."""
    with open(file_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()
