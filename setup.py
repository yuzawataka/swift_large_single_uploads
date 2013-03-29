from setuptools import setup, find_packages
import sys, os

version = '0.1'

setup(name='large_single_uploads',
      version=version,
      description="",
      long_description="""\
""",
      classifiers=[], # Get strings from http://pypi.python.org/pypi?%3Aaction=list_classifiers
      keywords='',
      author='',
      author_email='yuzawataka@intellilink.co.jp',
      url='',
      license='Apache License 2',
      packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          # -*- Extra requirements: -*-
      ],
      entry_points= {
        'paste.filter_factory': [
            'lsu=large_single_uploads.lsu:filter_factory',
            ],
        },
      )
