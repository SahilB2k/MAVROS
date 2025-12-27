
# operators/cpp_modules/__init__.py
# This file attempts to load the C++ module. 
# If it fails, HAS_CPP is set to False, triggerring Python fallback.

import sys
import os

HAS_CPP = False
inter_route_2opt_star_cpp = None
cross_exchange_cpp = None

# Try to import the compiled C++ module
try:
    # Add current directory to path to find the .pyd/.so file
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(current_dir)
    
    # Attempt import - name depends on what we call it in setup.py
    # We will call it 'mavros_cpp'
    import mavros_cpp
    
    HAS_CPP = True
    inter_route_2opt_star_cpp = mavros_cpp.inter_route_2opt_star
    cross_exchange_cpp = mavros_cpp.cross_exchange
    print("DEBUG: C++ Acceleration Module Loaded Successfully! 🚀")
    
except ImportError as e:
    # Silent fallback - or verbose if debugging
    # print(f"DEBUG: C++ Module not found ({e}). Using Python fallback. 🐍")
    HAS_CPP = False
except Exception as e:
    print(f"DEBUG: Error loading C++ module: {e}")
    HAS_CPP = False
