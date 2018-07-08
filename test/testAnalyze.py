import unittest

import analyze
import json

class TestAnalyze(unittest.TestCase):

    def testRendererIDs(self):
        trace = json.loads("""
            { "traceEvents": [
                { "pid": 123, "cat": "__metadata", "name": "process_name", "args": { "name": "Renderer" } },
                { "pid": 456, "cat": "__metadata", "name": "process_name", "args": { "name": "Renderer" } },
                { "pid": 789, "cat": "__metadata", "name": "process_name", "args": { "name": "Service: proxy_resolver" } },
                { "pid": 123, "tid": 111, "cat": "__metadata", "name": "thread_name", "args": { "name": "CrRendererMain" } },
                { "pid": 456, "tid": 222, "cat": "__metadata", "name": "thread_name", "args": { "name": "CrRendererMain" } }
            ] }""")
        ids = analyze.rendererIDs(trace)
        self.assertEquals([{"pid": 123, "tid": 111}, {"pid": 456, "tid": 222}], ids)

if __name__ == "__main__":
    unittest.main()
