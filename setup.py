from setuptools import setup, find_packages
from setuptools.command.install import install
import sys
import urllib.request
import subprocess

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

class CustomInstall(install):
    """Custom install class to download and install platform-specific wheels."""
    def run(self):
        # Detect the operating system
        if sys.platform.startswith('linux'):
            print("Linux detected. Downloading TA-Lib .deb package...")
            url = "https://github.com/ta-lib/ta-lib/releases/download/v0.6.4/ta-lib_0.6.4_amd64.deb"
            file_name = "ta-lib_0.6.4_amd64.deb"
            urllib.request.urlretrieve(url, file_name)
            
            # Install the .deb package
            subprocess.check_call(["sudo", "dpkg", "-i", file_name])

        elif sys.platform == "win32":
            print("Windows detected. Downloading TA-Lib .whl file...")
            url = "https://github.com/cgohlke/talib-build/releases/download/v0.6.3/ta_lib-0.6.3-cp313-cp313-win_amd64.whl"
            file_name = "ta_lib-0.6.3-cp313-cp313-win_amd64.whl"
            urllib.request.urlretrieve(url, file_name)
            
            # Install the .whl file
            subprocess.check_call([sys.executable, "-m", "pip", "install", file_name])

        else:
            print("Unsupported platform. Please manually install TA-Lib.")


        # Continue with the standard install process
        install.run(self)



setup(
    name="bitunix_automated_crypto_trading",
    version="1.6.0",
    author="tcj2001",
    author_email="thomsonmathews@hotmail.com",
    description="Bitunix Futures Auto Trading Platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tcj2001/bitunix-automated-crypto-trading",
    packages=find_packages(include=['src', 'src.*']),
    package_dir={'': '.'},
    include_package_data=True,
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
        #"TA-Lib",  # Technical Analysis Library
    ],
    entry_points={
        "console_scripts": [
            "bitunixautotrade=src.bitunix:main",
        ],
    },
    cmdclass={
        'install': CustomInstall,  # Override the install command
    },
    package_data={
        "": ["templates/*.html", "static/*", "config.txt", "sampleenv.txt"],
    },
)
