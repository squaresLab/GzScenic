import os
from glob import glob
from setuptools import setup, find_packages


setup(
    name='scenic-gazebo',
    version='0.1dev',
    description='TBA',
    author='Afsoon Afzal',
    author_email='afsoona@cs.cmu.edu',
    url='https://github.com/squaresLab/scenic-gazebo',
    license='mit',
    python_requires='>=3.8',
    install_requires = [
        'pytest==4.4.0',
        'pexpect==4.6.0',
        'attrs==20.1.0',
        'pyyaml==5.1',
        'ruamel.yaml==0.15.89',
        'matplotlib==3.3.2',
        'psutil==5.6.7',
    ],
    package_dir = {'': 'src'},
    packages = [
        'scenic-gazebo'
    ],
    entry_points = {
        'console_scripts': [
            'translate = translate:main',
        ]
    }
)
