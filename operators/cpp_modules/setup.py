
from setuptools import setup, Extension
import pybind11
import os

# Define the extension module
ext_modules = [
    Extension(
        "mavros_cpp",
        ["inter_route_2opt_star.cpp"],
        include_dirs=[pybind11.get_include()],
        language='c++'
    ),
]

setup(
    name="mavros_cpp",
    version="1.0",
    description="Accelerated C++ operators for MAVROS VRPTW Solver",
    ext_modules=ext_modules,
)
