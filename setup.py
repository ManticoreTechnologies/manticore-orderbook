"""
Setup script for manticore-orderbook.
"""

from setuptools import setup, find_packages

setup(
    name="manticore-orderbook",
    version="1.0.1",
    packages=find_packages(),
    install_requires=[
        "tabulate>=0.8.9",
    ],
    author="Manticore Technologies",
    author_email="dev@manticore.technology",
    description="A high-performance order book implementation for cryptocurrency exchanges",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/manticoretechnologies/manticore-orderbook",
    project_urls={
        "Homepage": "https://manticore.technology",
        "Bug Tracker": "https://github.com/manticoretechnologies/manticore-orderbook/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Financial and Insurance Industry",
        "Topic :: Office/Business :: Financial :: Investment",
    ],
    python_requires=">=3.8",
) 