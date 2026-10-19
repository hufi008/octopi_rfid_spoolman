from setuptools import setup, find_packages

setup(
    name="octopi_rfid_spoolman",
    version="0.2.1",
    packages=find_packages(),
    package_data={"octopi_rfid_spoolman": ["templates/*.jinja2", "static/js/*.js"]},
    install_requires=[
        "requests",
        "spidev",
        "mfrc522",
    ],
    entry_points={
        "console_scripts": [
            "octopi-rfid-spoolman=octopi_rfid_spoolman.main:main",
        ],
        "octoprint.plugin": [
            "rfid_spoolman=octopi_rfid_spoolman",
        ],
    },
)
