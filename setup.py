import pathlib
from setuptools import setup

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

# This call to setup() does all the work
setup(
    name="CSIKit",
    version="1.0.0",
    description="Tools for extracting Channel State Information from files produced by a range of WiFi hardware/drivers.",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://github.com/Gi-z/CSIKit",
    author="Glenn Forbes",
    author_email="g.r.forbes@rgu.ac.uk",
    license="MIT",
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.5",
    ],
    packages=["CSIKit", "CSIKit.tools"],
    include_package_data=True,
    install_requires=["Cython", "numpy", "matplotlib", "scikit-learn"],
    entry_points={
        "console_scripts": [
            "CSIKit=CSIKit.__main__:main",
        ]
    },
)