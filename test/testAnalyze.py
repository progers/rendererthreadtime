import unittest

import analyze
import json

class TestAnalyze(unittest.TestCase):

    def testRendererPIDs(self):
        trace = json.loads("""
            { "traceEvents": [
                { "pid": 123, "cat": "__metadata", "name": "process_name", "args": { "name": "Renderer" } },
                { "pid": 456, "cat": "__metadata", "name": "process_name", "args": { "name": "Renderer" } },
                { "pid": 789, "cat": "__metadata", "name": "process_name", "args": { "name": "Service: proxy_resolver" } }
            ] }""")
        pids = analyze.rendererPIDs(trace)
        self.assertEquals([123, 456], pids)

if __name__ == "__main__":
    unittest.main()
