
from setuptools import setup, find_packages

setup(
  name='nr.collections',
  version='0.9.0.dev0',
  packages=find_packages('src', exclude=['test*']),
  package_dir={'': 'src'},
  install_requires=['nr.metaclass']
)