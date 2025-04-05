from setuptools import setup, find_packages
from setuptools.command.install import install
from setuptools.command.sdist import sdist
import sys
import urllib.request
import subprocess
import re
import os

class CustomInstall(install):
    """Custom install class to download and install platform-specific TA-Lib wheels.
    This avoids building TA-Lib from source, which can be problematic.
    """
    def run(self):
        # First run the standard installation process
        install.run(self)

        # Then handle TA-Lib installation separately
        self.install_talib()

    def install_talib(self):
        # Detect the operating system
        platform = sys.platform
        try:
            # First try to import TA-Lib to see if it's already installed
            import talib
            print(f"TA-Lib is already installed. Available functions: {len(talib.get_functions())}")
            return  # TA-Lib is already installed, so we're done
        except ImportError:
            # TA-Lib is not installed, so download and install the wheel
            if platform == "win32":
                print("\n------------------------------------------------------")
                print("Windows detected. Installing TA-Lib from pre-built wheel...")
                print("------------------------------------------------------\n")
                url = "https://github.com/cgohlke/talib-build/releases/download/v0.6.3/ta_lib-0.6.3-cp313-cp313-win_amd64.whl"
                file_name = "ta_lib-0.6.3-cp313-cp313-win_amd64.whl"
                try:
                    print(f"Downloading {url}...")
                    urllib.request.urlretrieve(url, file_name)
                    # Install the .whl file with --no-build-isolation to prevent building from source
                    print(f"Installing {file_name}...")
                    subprocess.check_call([sys.executable, "-m", "pip", "install", file_name, "--no-build-isolation"])
                    print("TA-Lib wheel installed successfully.")
                except Exception as e:
                    print(f"Error installing TA-Lib wheel: {e}")
                    print("\nPlease install TA-Lib manually:")
                    print("pip install https://github.com/cgohlke/talib-build/releases/download/v0.6.3/ta_lib-0.6.3-cp313-cp313-win_amd64.whl")
            elif platform.startswith('linux'):
                print(f"\n------------------------------------------------------")
                print(f"Platform {platform} detected. installing TA-Lib.")
                print("------------------------------------------------------\n")
                url = "https://github.com/ta-lib/ta-lib/releases/download/v0.6.4/ta-lib_0.6.4_amd64.deb"
                file_name = "ta-lib_0.6.4_amd64.deb"
                try:
                    print(f"Downloading {url}...")
                    urllib.request.urlretrieve(url, file_name)
                    print(f"Installing {file_name}...")
                    subprocess.check_call(["sudo", "dpkg", "-i", file_name])
                    print("TA-Lib wheel installed successfully.")
                except Exception as e:
                    print(f"Error installing TA-Lib wheel: {e}")
                    print("For Linux, you can use:")
                    print("wget https://github.com/ta-lib/ta-lib/releases/download/v0.6.4/ta-lib_0.6.4_amd64.deb")
                    print("sudo dpkg -i ta-lib_0.6.4_amd64.deb")
                    print("pip install TA-Lib")

setup(
    name="bitunix_automated_crypto_trading",
    version="2.6.8",
    license="MIT",
    author="tcj2001",
    author_email="thomsonmathews@hotmail.com",
    description="Bitunix Futures Auto Trading Platform",
    url="https://github.com/tcj2001/bitunix-automated-crypto-trading",
    packages=find_packages(),

    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.13",  # Required for the TA-Lib wheel compatibility
    install_requires=[
        "fastapi",
        "uvicorn",
        "fastapi-login",
        "python-multipart",
        "jinja2",
        "python-dotenv",
        "pydantic",
        "pydantic-settings",
        "websockets",
        "requests",
        "aiohttp",
        "pytz",
        "cryptography",
        "colorama",
        "pandas",
        "numpy",
        # TA-Lib is handled separately in the CustomInstall class
    ],
    entry_points={
        "console_scripts": [
            "bitunixautotrade=bitunix_automated_crypto_trading.bitunix:app",
        ],
    },
    cmdclass={
        'install': CustomInstall,  # Override the install command
    },
    package_data={
        "": ["requirements.txt", "README.md"],
    },
    # Include non-code files in the package
    include_package_data=True,
)
