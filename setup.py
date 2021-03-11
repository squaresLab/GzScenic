import os
from glob import glob
from setuptools import setup, find_packages


setup(
    name='gzscenic',
    version='0.1dev',
    description='Automatic scene generation for Gazebo',
    author='Afsoon Afzal',
    author_email='afsoona@cs.cmu.edu',
    url='https://github.com/squaresLab/GzScenic',
    license='BSD-3-Clause',
    python_requires='>=3.8',
    include_package_data=True,
    install_requires = [
        'pytest==4.4.0',
        'pexpect==4.6.0',
        'attrs>=19.3.0',
        'pyyaml==5.1',
        'ruamel.yaml==0.15.89',
        'matplotlib==3.3.2',
        'psutil==5.6.7',
        'wget==3.2',
        'pycollada==0.7.1',
        'pywavefront==1.3.3',
        'numpy==1.19.4',
        'scenic==2.0.0',
        'requests>=2.25.1'
    ],
    packages = find_packages(),
    entry_points = {
        'console_scripts': [
            'gzscenic = gzscenic.gzscenic:main',
        ]
    }
)
