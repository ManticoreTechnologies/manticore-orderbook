"""
Setup script for manticore-orderbook.
"""

from setuptools import setup, find_packages

setup(
    name="manticore-orderbook",
    version="0.3.0",
    description="High-performance order book management for trading systems",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author="Manticore Technologies",
    author_email="info@example.com",
    url="https://github.com/yourusername/manticore-orderbook",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
) 