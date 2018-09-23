import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="trackimo",
    version="0.0.5",
    author="Troy Kelly",
    author_email="troy@troykelly.com",
    description="Access GPS location data of your Trackimo devices",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/troykelly/python-trackimo",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
    ],
)
