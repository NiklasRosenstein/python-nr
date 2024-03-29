# This file was auto-generated by Shut. DO NOT EDIT
# For more information about Shut, check out https://pypi.org/project/shut/

from __future__ import print_function
import io
import os
import setuptools
import sys

def _tempcopy(src, dst):
  import atexit, shutil
  if not os.path.isfile(dst):
    if not os.path.isfile(src):
      command = sys.argv[1] if len(sys.argv) >= 2 else None
      msg = '"{}" does not exist, and cannot copy it from "{}" either'.format(dst, src)
      # NOTE: In dist/build commands that are not invoked by Pip, we enforce that the license file
      #       must be present. See https://github.com/NiklasRosenstein/shut/issues/22
      if command and 'PIP_REQ_TRACKER' not in os.environ and ('build' in command or 'dist' in command):
        raise RuntimeError(msg)
      print('warning:', msg, file=sys.stderr)
      return
    shutil.copyfile(src, dst)
    atexit.register(lambda: os.remove(dst))


_tempcopy('../LICENSE.txt', 'LICENSE.txt')

readme_file = 'readme.md'
if os.path.isfile(readme_file):
  with io.open(readme_file, encoding='utf8') as fp:
    long_description = fp.read()
else:
  print("warning: file \"{}\" does not exist.".format(readme_file), file=sys.stderr)
  long_description = None

requirements = [
  'overrides >=3.1.0,<4.0.0',
  'nr.pylang.utils >=0.1.3,<1.0.0',
]

setuptools.setup(
  name = 'nr.caching',
  version = '0.4.1',
  author = 'Niklas Rosenstein',
  author_email = 'rosensteinniklas@gmail.com',
  description = 'A simple key-value caching API with default implementations for an SQLite3 storage backend and a JSON convenience layer.',
  long_description = long_description,
  long_description_content_type = 'text/markdown',
  url = 'https://github.com/NiklasRosenstein/nr-python',
  license = 'MIT',
  packages = setuptools.find_packages('src', ['test', 'test.*', 'tests', 'tests.*', 'docs', 'docs.*']),
  package_dir = {'': 'src'},
  include_package_data = True,
  install_requires = requirements,
  extras_require = {},
  tests_require = [],
  python_requires = '>=3.6.0,<4.0.0',
  data_files = [],
  entry_points = {},
  cmdclass = {},
  keywords = [],
  classifiers = [],
  zip_safe = False,
)
