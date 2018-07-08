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
        self.assertEquals([(123, 111), (456, 222)], ids)

    def testGroupedEvents(self):
        trace = json.loads("""
            { "traceEvents": [
                { "pid": 123, "tid": 111, "ph": "X", "name": "event1", "ts": 123, "dur": 1},
                { "pid": 123, "tid": 111, "ph": "X", "name": "event2", "ts": 124, "dur": 1}
            ] }""")
        events = analyze.groupedEvents(trace, [(123, 111)])
        self.assertEquals(2, len(events[(123, 111)]))
        self.assertEquals({'begin': 123, 'end': 124, 'name': u'event1'}, events[(123, 111)][0])
        self.assertEquals({'begin': 124, 'end': 125, 'name': u'event2'}, events[(123, 111)][1])

if __name__ == "__main__":
    unittest.main()
