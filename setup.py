from setuptools import setup, find_packages

setup(
    name="cli-weather",
    version="0.1.0",
    author="Onehand Coding",
    author_email="onehand.coding433@gmail.com",
    description="A CLI weather application",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/Phoenix1025/CLI-weather",
    packages=find_packages(),
    install_requires=[
        "tzdata",
        "geopy",
        "requests",
        "python-dotenv"
    ],
    python_requires=">=3.7",
    entry_points={
        "console_scripts": [
            "cli-weather=cli_weather.main:main",
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
