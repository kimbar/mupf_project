from setuptools import setup, find_namespace_packages

setup(
    name="mupf",
    version="0.1",
    packages=find_namespace_packages(include=('mupf', 'mupf.*', 'mupf.plugins')),
    install_requires=[
    	'websockets>=7.0',
    ]
)
