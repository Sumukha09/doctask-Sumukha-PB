#!/usr/bin/env python
import os
import sys

# Add the current directory to PYTHONPATH so imports from `app` work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.mcp.server import main

if __name__ == "__main__":
    main()
