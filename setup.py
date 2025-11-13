from setuptools import setup, find_packages

setup(
    name="pudao",
    version="0.0.0",
    packages=find_packages(exclude=("tests", "docs")),
    include_package_data=True,
    install_requires=[],
    entry_points={
        'console_scripts': [
            'pudao = pudao.cli.pudao_cli:main',
        ],
    },
)
