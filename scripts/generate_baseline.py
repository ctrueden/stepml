#!/usr/bin/env python3
"""
Generate baseline feature extractions for regression testing.

This is a convenience wrapper that runs the actual script from the stepml package.
"""
import sys
from pathlib import Path

if __name__ == "__main__":
    # Add src directory to path so stepml can be imported
    project_root = Path(__file__).parent.parent
    src_dir = project_root / "src"
    sys.path.insert(0, str(src_dir))
    
    # Now import and run the actual script
    from stepml.scripts.generate_baseline import generate_baseline
    generate_baseline()
