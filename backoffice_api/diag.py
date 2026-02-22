import sys
import os

def diag():
    print("PYTHONPATH:", sys.path)
    print("CWD:", os.getcwd())
    try:
        import src
        print("src module found at:", src.__file__)
    except ImportError as e:
        print("src module NOT found:", e)

if __name__ == "__main__":
    diag()
