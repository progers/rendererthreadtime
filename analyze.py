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

# Compute each event self time.
# TODO(pdr): Expand this comment.
def addSelfTime(events):
    # This is a naive O(n^2) approach.
    for event in events:
        selfTime = event["end"] - event["begin"]
        for other in events:
            if event == other:
                continue
            if other["begin"] >= event["begin"] and other["end"] <= event["end"]:
                selfTime -= (other["end"] - other["begin"])
        event["self"] = selfTime

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

# Returns events from renderer threads.
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
    return events

def analyze(traceFile):
    with open(traceFile) as f:
        traceJson = json.load(f)
    events = rendererEvents(traceJson["traceEvents"])

    # TODO(pdr): Analyze the events and show the most expensive self-time categories.
    addSelfTime(events)
    print "event count: " + str(len(events))

def main():
    parser = argparse.ArgumentParser(description="Analyze main thread time")
    parser.add_argument("trace", help="Trace to analyze, in json format")
    args, leftover = parser.parse_known_args()
    analyze(args.trace)

if __name__ == "__main__":
    main()
