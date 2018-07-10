import unittest

import analyze
import json

class TestAnalyze(unittest.TestCase):

    def testRendererIds(self):
        traceEvents = [
                { "pid": 123, "cat": "__metadata", "name": "process_name", "args": { "name": "Renderer" } },
                { "pid": 456, "cat": "__metadata", "name": "process_name", "args": { "name": "Renderer" } },
                { "pid": 789, "cat": "__metadata", "name": "process_name", "args": { "name": "Service: proxy_resolver" } },
                { "pid": 123, "tid": 111, "cat": "__metadata", "name": "thread_name", "args": { "name": "CrRendererMain" } },
                { "pid": 456, "tid": 222, "cat": "__metadata", "name": "thread_name", "args": { "name": "CrRendererMain" } } ]
        ids = analyze._rendererIds(traceEvents)
        self.assertEquals([(123, 111), (456, 222)], ids)

    def testRendererEvents(self):
        traceEvents = [
                { "pid": 111, "cat": "__metadata", "name": "process_name", "args": { "name": "Renderer" } },
                { "pid": 111, "tid": 222, "cat": "__metadata", "name": "thread_name", "args": { "name": "CrRendererMain" } },
                { "pid": 111, "tid": 222, "ph": "X", "name": "event1", "ts": 123, "dur": 1},
                { "pid": 111, "tid": 222, "ph": "X", "name": "event2", "ts": 124, "dur": 1} ]
        events = analyze.rendererEvents(traceEvents)
        self.assertEquals(2, len(events))
        self.assertEquals({"begin": 123, "end": 124, "name": "event1", "self": 1}, events[0])
        self.assertEquals({"begin": 124, "end": 125, "name": "event2", "self": 1}, events[1])

    def testSelfTimeForConcurrentEventsInDifferentThreads(self):
        traceEvents = [
                { "pid": 111, "cat": "__metadata", "name": "process_name", "args": { "name": "Renderer" } },
                { "pid": 111, "tid": 222, "cat": "__metadata", "name": "thread_name", "args": { "name": "CrRendererMain" } },
                { "pid": 555, "cat": "__metadata", "name": "process_name", "args": { "name": "Renderer" } },
                { "pid": 555, "tid": 666, "cat": "__metadata", "name": "thread_name", "args": { "name": "CrRendererMain" } },
                { "pid": 111, "tid": 222, "ph": "X", "name": "a", "ts": 1, "dur": 5},
                { "pid": 555, "tid": 666, "ph": "X", "name": "b", "ts": 2, "dur": 2} ]
        events = analyze.rendererEvents(traceEvents)
        self.assertEquals(2, len(events))
        self.assertEquals("a", events[0]["name"])
        self.assertEquals(5, events[0]["self"])
        self.assertEquals("b", events[1]["name"])
        self.assertEquals(2, events[1]["self"])

    def testSelfTimeSimpleNest(self):
        # Pattern being tested:
        #   [  a      ]
        #       [ b   ]
        events = [ {"begin": 1, "end": 4, "name": "a"}, {"begin": 2, "end": 4, "name": "b"} ]
        analyze._computeSelfTimes(events)
        self.assertEquals(1, events[0]["self"])
        self.assertEquals(2, events[1]["self"])

    def testSelfTimeMultipleTopLevels(self):
        # Pattern being tested:
        #   [  a  ] [  b  ]
        events = [ {"begin": 1, "end": 2, "name": "a"}, {"begin": 2, "end": 3, "name": "b"} ]
        analyze._computeSelfTimes(events)
        self.assertEquals(1, events[0]["self"])
        self.assertEquals(1, events[1]["self"])

    def testSelfTimeMultipleNested(self):
        # Pattern being tested:
        #   [   a   ]
        #    [b] [c]
        events = [ {"begin": 1, "end": 6, "name": "a"}, {"begin": 2, "end": 3, "name": "b"}, {"begin": 4, "end": 5, "name": "c"} ]
        analyze._computeSelfTimes(events)
        self.assertEquals(3, events[0]["self"])
        self.assertEquals(1, events[1]["self"])
        self.assertEquals(1, events[2]["self"])

    def testSelfTimeWithCompletelyOverlappingEvents(self):
        # Pattern being tested:
        #   [  a  ]
        #   [  b  ]
        #   [  c  ]
        events = [ {"begin": 1, "end": 4, "name": "a"}, {"begin": 1, "end": 4, "name": "b"}, {"begin": 1, "end": 4, "name": "c"} ]
        analyze._computeSelfTimes(events)
        self.assertEquals(0, events[0]["self"])
        self.assertEquals(0, events[1]["self"])
        self.assertEquals(3, events[2]["self"])

    def testSelfTimeWithDoublyNestedEvents(self):
        # Pattern being tested:
        #   [ a ]
        #    [ b]
        #     [c]
        events = [ {"begin": 1, "end": 4, "name": "a"}, {"begin": 2, "end": 4, "name": "b"}, {"begin": 3, "end": 4, "name": "c"} ]
        analyze._computeSelfTimes(events)
        self.assertEquals(1, events[0]["self"])
        self.assertEquals(1, events[1]["self"])
        self.assertEquals(1, events[2]["self"])

    # Integration test that checks that the sum of the time spent in top-level
    # events equals the sum of all self-time.
    def testSelfTimeSumsToTotalTopLevelTime(self):
        testTraceFile = "test/data/pr.gg_load.json"
        with open(testTraceFile) as f:
            traceJson = json.load(f)
        rendererIds = analyze._rendererIds(traceJson["traceEvents"])
        eventsById = analyze._eventsById(traceJson["traceEvents"], rendererIds)

        for id in eventsById:
            topLevelEventTime = 0
            totalSelfTime = 0
            events = eventsById[id]
            for event in events:
                totalSelfTime += event["self"]
                hasContainingEvent = False
                for other in events:
                    if other["begin"] > event["begin"] or other["end"] < event["end"]:
                        continue
                    # If there are two events with equal begin and end times,
                    # the earlier event in the trace file should contain the
                    # later. This also prevents an event from containing itself.
                    if other["begin"] == event["begin"] and other["end"] == event["end"]:
                        if events.index(other) >= events.index(event):
                            continue
                    hasContainingEvent = True
                    break
                if not hasContainingEvent:
                    topLevelEventTime += event["end"] - event["begin"]

            self.assertEquals(topLevelEventTime, totalSelfTime)

if __name__ == "__main__":
    unittest.main()
