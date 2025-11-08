from setuptools import setup, find_packages

setup(
    name="queuectl",
    version="1.0.0",
    description="CLI-based background job queue system",
    author="Your Name",
    packages=find_packages(),
    install_requires=[
        "click>=8.1.7",
        "sqlalchemy>=2.0.23",
        "flask>=3.0.0",
    ],
    entry_points={
        "console_scripts": [
            "queuectl=queuectl.cli:main",
        ],
    },
    python_requires=">=3.8",
)

