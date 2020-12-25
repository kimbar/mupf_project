from setuptools import setup, find_packages

setup(
    name="mupf-dev-tools",
    version="0.1",
    py_modules=['mupfdevtools'],
    install_requires=[
        'nox',
    ]
)
