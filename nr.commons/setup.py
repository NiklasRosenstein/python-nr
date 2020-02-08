
import io
import re
import setuptools
import sys

with io.open('src/nr/commons/__init__.py', encoding='utf8') as fp:
  version = re.search(r"__version__\s*=\s*'(.*)'", fp.read()).group(1)

long_description = None

requirements = []
extras_require = {}
extras_require['test'] = ['nr.collections >=0.1.0,<1.0.0']
tests_require = []
tests_require = ['nr.collections >=0.1.0,<1.0.0']

setuptools.setup(
  name = 'nr.commons',
  version = version,
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = "Provides common utilities that didn't make it into any of the other nr namespace packages.",
  long_description = long_description,
  long_description_content_type = 'text/plain',
  url = 'https://git.niklasrosenstein.com/NiklasRosenstein/nr-python-libs',
  license = 'MIT',
  packages = setuptools.find_packages('src', ['test', 'test.*', 'docs', 'docs.*']),
  package_dir = {'': 'src'},
  include_package_data = False,
  install_requires = requirements,
  extras_require = extras_require,
  tests_require = tests_require,
  python_requires = None, # TODO: None,
  data_files = [],
  entry_points = {},
  cmdclass = {}
)
