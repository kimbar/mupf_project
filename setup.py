from setuptools import setup, find_packages

setup(
    name="mupf",
    version="0.1",
    packages=find_packages(),
    install_requires=[
    	'websockets>=7.0',
    	'selenium>=3',    # for automated GUI testing
        'nose>=1.3',      # for developement testing
    ]
)
