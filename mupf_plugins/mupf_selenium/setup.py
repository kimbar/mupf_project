from setuptools import setup, find_namespace_packages

setup(
    name="mupf-selenium",
    version="0.1",
    packages=find_namespace_packages(include=('mupf.plugins', 'mupf.plugins.*')),
    install_requires=[
    	'mupf',
        'selenium',
    ]
)