from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="bitunix-automated-crypto-trading",
    version="1.2.0",
    author="tcj2001",
    author_email="thomsonmathews@hotmail.com",
    description="Bitunix Futures Auto Trading Platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tcj2001/bitunix-automated-crypto-trading",
    packages=find_packages(),
    include_package_data=True,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
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
        # Note: TA-LIB is commented out as it requires special installation
        # "TA-LIB",
    ],
    entry_points={
        "console_scripts": [
            "bitunix=bitunix:main",
        ],
    },
    package_data={
        "": ["templates/*.html", "static/*", "config.txt", "sampleenv.txt"],
    },
)
