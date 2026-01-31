import sys
from pathlib import Path

# Add the project root to the Python path to allow imports from 'pal'
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
