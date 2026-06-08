"""Entry point so the engine can be run with ``python -m engine``."""

from .pipeline import run

if __name__ == "__main__":
    d = run()
    print("as_of=%s  index=%s  regime=%s" % (d["as_of"], d["index"], d["regime"]))
