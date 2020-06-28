import platform
import sys
from pathlib import Path

from setuptools import setup, find_packages

assert sys.version_info >= (3, 6, 0), "we require Python 3.6+"

if platform.system() != "Windows":
    print("We support only Windows at the moment! Proceed at your own risk.")

HERE = Path(__file__).parent
sys.path.insert(0, str(HERE))  # setuptools.build_meta needs this


def get_long_description() -> str:
    return (HERE / "README.md").read_text(encoding="utf8")


setup(
    name="flowd",
    description="Collector of metrics for the Flow State detection system.",
    long_description=get_long_description(),
    long_description_content_type="text/markdown",
    url="https://github.com/henrykp/fs_collect",
    license="MIT",
    python_requires=">=3.6",
    zip_safe=False,
    packages=find_packages(),
    install_requires=[
        'wheel',
        'scipy==1.4.1',
        'numba==0.48',
        # 'torch@https://download.pytorch.org/whl/cpu/torch-1.5.1%2Bcpu-cp36-cp36m-win_amd64.whl',
        'webrtcvad>=2.0.10',
        'psutil',
        'pyaudio',
        'pyannote.audio>=2.0a1'
    ],
    extras_require={},
    entry_points={"console_scripts": ["flowd=flowd.__main__:main"]},
)
