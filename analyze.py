#!/usr/bin/env python

# analyze.py - analyze renderer thread time from a trace file.
#
# Usage:
#   1) Navigate to chrome://tracing, record a trace with the categories:
#      blink, cc, gpu, loading, mojom, toplevel, v8
#   2) In a new tab, navigate to some page.
#   3) In chrome://tracing, stop tracing and save the trace.
#   4) Uncompress the trace file with "gunzip [trace_file.json].gz".
#   5) Run analyze.py trace_file.json

import argparse
import json

# Compute each event's self time which is the time spent in the event minus the
# time spent in all other events occurring at the same time.
def _computeSelfTimes(events):
    def selfTime(event, events):
        if "self" in event:
            return event["self"]
        begin = event["begin"]
        end = event["end"]
        otherSelf = 0
        for other in events:
            if other["begin"] < begin or other["end"] > end:
                continue;
            # If there are two events with equal begin and end times, the later
            # event in the trace file should get the self time.
            if other["begin"] == begin and other["end"] == end:
                if events.index(other) <= events.index(event):
                    continue
            otherSelf += selfTime(other, events)
        event["self"] = end - begin - otherSelf
        return event["self"]

    # This is a naive approach where we recursively compute self time and
    # memoize the result as we go.
    for event in events:
        selfTime(event, events)

# Returns the list of renderer (PID, TID) tuples.
def _rendererIds(traceEvents):
    pids = []
    for event in traceEvents:
        if event.get("cat") != "__metadata":
            continue
        if event.get("name") != "process_name":
            continue
        if event.get("args").get("name") != "Renderer":
            continue
        pids.append(event["pid"])
    ids = []
    for event in traceEvents:
        if event.get("cat") != "__metadata":
            continue
        if event.get("name") != "thread_name":
            continue
        if event.get("args").get("name") != "CrRendererMain":
            continue
        if not event.get("pid") in pids:
            continue
        pidtid = (event["pid"], event["tid"])
        ids.append(pidtid)
    return ids

# Returns events from renderer threads. Each event has a name, begin, end, and
# self time.
def rendererEvents(traceEvents):
    rendererIds = _rendererIds(traceEvents)
    events = []
    for traceEvent in traceEvents:
        if traceEvent.get("ph") != "X":
            continue
        id = (traceEvent["pid"], traceEvent["tid"])
        if not id in rendererIds:
            continue

        name = traceEvent["name"]
        begin = traceEvent["ts"]
        if not "dur" in traceEvent:
            # TODO(pdr): Figure out why this happens.
            continue
        end = begin + traceEvent["dur"]

        events.append({"name": name, "begin": begin, "end": end})

    _computeSelfTimes(events)
    return events

def analyze(traceFile):
    with open(traceFile) as f:
        traceJson = json.load(f)
    events = rendererEvents(traceJson["traceEvents"])

    # TODO(pdr): Analyze the events and show the most expensive self-time categories.
    print "event count: " + str(len(events))

def main():
    parser = argparse.ArgumentParser(description="Analyze main thread time")
    parser.add_argument("trace", help="Trace to analyze, in json format")
    args, leftover = parser.parse_known_args()
    analyze(args.trace)

if __name__ == "__main__":
    main()
