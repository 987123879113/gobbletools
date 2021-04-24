from distutils.core import setup
from Cython.Build import cythonize

setup(
    ext_modules = cythonize(["comp573.pyx", "enc573.pyx", "sum573.pyx"], annotate=True, language_level=3)
)
