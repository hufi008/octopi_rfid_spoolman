from setuptools import setup, find_packages

setup(
    name="octopi_rfid_spoolman",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests",
        "spidev",
        "mfrc522"
    ],
    entry_points={
        "console_scripts": [
            "octopi-rfid-spoolman=octopi_rfid_spoolman.main:main",
        ],
    },
)
