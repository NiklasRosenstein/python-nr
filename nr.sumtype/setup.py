
import io
import re
import setuptools
import sys

with io.open('src/nr/sumtype.py', encoding='utf8') as fp:
  version = re.search(r"__version__\s*=\s*'(.*)'", fp.read()).group(1)

with io.open('README.md', encoding='utf8') as fp:
  long_description = fp.read()

requirements = ['nr.metaclass >=0.9.0,<1.0.0', 'nr.stream >=0.9.0,<1.0.0']

setuptools.setup(
  name = 'nr.sumtype',
  version = version,
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'Sumtypes in Python.',
  long_description = long_description,
  long_description_content_type = 'text/markdown',
  url = 'https://git.niklasrosenstein.com/NiklasRosenstein/nr-python-libs',
  license = 'MIT',
  packages = setuptools.find_packages('src'),
  package_dir = {'': 'src'},
  include_package_data = False,
  install_requires = requirements,
  tests_require = [],
  python_requires = None, # TODO: None,
  entry_points = {}
)
