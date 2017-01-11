from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

root = path.dirname(__file__)
with open(path.join(root, 'vidutils', 'version.py'), encoding='utf-8') as f:
    exec(f.read())

short_description = ("scripts to automate some complex video editing steps"
        " with ffmpeg.")
setup(
    name='vidutils',
    version=version,
    description=short_description,
    long_description=long_description,
    url='https://github.com/gammafunk/vidutils',
    author='gammafunk',
    author_email='gammafunk@gmail.com',
    packages=['vidutils'],
    extras_require={},
    setup_requires = [],
    data_files=[],
    entry_points={
        'console_scripts': [
            'vid-volume=vidutils.volume:main',
            'vid-merge=vidutils.merge:main',
            'vid-split=vidutils.split:main',
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Multimedia :: Video",
        "License :: OSI Approved :: GNU General Public License v2 (GPLv2)",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
    ],
    platforms='all',
    license='GPLv2',
)
