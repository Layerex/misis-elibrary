import setuptools

module_name = "misis_elibrary"
from misis_elibrary import __prog__, __desc__, __version__

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setuptools.setup(
    name=__prog__,
    version=__version__,
    author="Layerex",
    author_email="layerex@dismail.de",
    description=__desc__,
    long_description=long_description,
    long_description_content_type="text/markdown",
    url=f"https://github.com/Layerex/{__prog__}",
    classifiers=[
        "Development Status :: 6 - Mature",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Topic :: Utilities",
    ],
    py_modules=[module_name],
    entry_points={
        "console_scripts": [
            f"{__prog__} = {module_name}:main",
        ],
    },
    install_requires=["requests", "img2pdf", "beautifulsoup4"],
)
