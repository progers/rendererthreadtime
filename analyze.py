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

# Returns a map of (PID,TID) to a list of trace events.
def groupedEvents(trace_json, pidtids):
    events = {}
    for event in trace_json["traceEvents"]:
        if not event["ph"] == "X":
            continue
        pidtid = (event["pid"], event["tid"])
        if not pidtid in pidtids:
            continue

        name = event["name"]
        begin = event["ts"]
        end = begin + event["dur"]

        if not pidtid in events:
            events[pidtid] = []
        events[pidtid].append({"name": name, "begin": begin, "end": end})
    return events

# Returns a list of renderer process (PID) and thread (TID) ids.
def rendererIDs(trace_json):
    pids = []
    for event in trace_json["traceEvents"]:
        if not event["cat"] == "__metadata":
            continue
        if not event["name"] == "process_name":
            continue
        if not event["args"]["name"] == "Renderer":
            continue
        pids.append(event["pid"])
    ids = []
    for event in trace_json["traceEvents"]:
        if not event["cat"] == "__metadata":
            continue
        if not event["name"] == "thread_name":
            continue
        if not event["args"]["name"] == "CrRendererMain":
            continue
        if not event["pid"] in pids:
            continue
        pidtid = (event["pid"], event["tid"])
        ids.append(pidtid)
    return ids

def analyze(trace_file):
    with open(trace_file) as f:
        trace_json = json.load(f)
    print "Renderers: " + str(rendererIDs(trace_json))

def main():
    parser = argparse.ArgumentParser(description="Analyze main thread time")
    parser.add_argument("trace", help="Trace to analyze, in json format")
    args, leftover = parser.parse_known_args()
    analyze(args.trace)

if __name__ == "__main__":
    main()
