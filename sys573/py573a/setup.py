from distutils.core import setup
from Cython.Build import cythonize

setup(
    ext_modules = cythonize(["enc573.pyx"], annotate=True, language_level=3)
)
