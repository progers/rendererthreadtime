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
import operator
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

# Returns events grouped by id tuple (process & thread). Each event has a name,
# begin, end, and self time.
def _eventsById(traceEvents, ids):
    eventsById = {}
    for traceEvent in traceEvents:
        if traceEvent.get("ph") != "X":
            continue
        id = (traceEvent["pid"], traceEvent["tid"])
        if not id in ids:
            continue

        name = traceEvent["name"]
        begin = traceEvent["ts"]
        if not "dur" in traceEvent:
            # TODO(pdr): Figure out why this happens.
            continue
        end = begin + traceEvent["dur"]

        if not id in eventsById:
            eventsById[id] = []
        eventsById[id].append({"name": name, "begin": begin, "end": end})

    for id in eventsById:
        # Compute self times using events within a process & thread.
        _computeSelfTimes(eventsById[id])

    return eventsById

# Returns events from renderer threads.
def rendererEvents(traceEvents):
    rendererIds = _rendererIds(traceEvents)
    eventsById = _eventsById(traceEvents, rendererIds)
    events = []
    for id in eventsById:
        events.extend(eventsById[id])
    return events

# Return the category for an event.
def category(eventName):
    if (eventName == "ThreadControllerImpl::DoWork"): return "unknown task"
    if (eventName == "TimerBase::run"): return "unknown timer"

    if (eventName == "BackgroundHTMLParser::pumpTokenizer"): return "parsing"
    if (eventName == "BackgroundHTMLParser::sendTokensToMainThread"): return "parser"
    if (eventName == "CommandBufferProxyImpl::Initialize"): return "gpu"
    if (eventName == "CompositingInputsUpdater::update"): return "compositing"
    if (eventName == "CompositingLayerAssigner::assign"): return "compositing"
    if (eventName == "CompositingRequirementsUpdater::updateRecursive"): return "compositing"
    if (eventName == "ContextCreatedNotification"): return "v8"
    if (eventName == "DisplayItemList::Finalize"): return "paint"
    if (eventName == "Document::rebuildLayoutTree"): return "stylelayout"
    if (eventName == "Document::recalcStyle"): return "stylelayout"
    if (eventName == "Document::updateActiveStyle"): return "stylelayout"
    if (eventName == "Document::updateStyleInvalidationIfNeeded"): return "stylelayout"
    if (eventName == "EventHandler::HitTestResultAtLocation"): return "hittest"
    if (eventName == "EventHandler::handleMouseMoveEvent"): return "events"
    if (eventName == "GraphicsLayer::PaintContents"): return "paint"
    if (eventName == "GraphicsLayerTreeBuilder::rebuild"): return "compositing"
    if (eventName == "GraphicsLayerUpdater::update"): return "compositing"
    if (eventName == "HTMLDocumentParser::EnqueueTokenizedChunk"): return "parser"
    if (eventName == "HTMLDocumentParser::processTokenizedChunkFromBackgroundParser"): return "parser"
    if (eventName == "HTMLParserScriptRunner ExecuteScript"): return "script"
    if (eventName == "HTMLParserScriptRunner::execute"): return "v8"
    if (eventName == "LayerTreeHost::DoUpdateLayers"): return "cc"
    if (eventName == "LayerTreeHost::UpdateLayers::BuildPropertyTrees"): return "ccproptrees"
    if (eventName == "LocalFrameView::UpdateViewportIntersectionsForSubtree"): return "intersectionobserver"
    if (eventName == "LocalFrameView::layout"): return "stylelayout"
    if (eventName == "LocalFrameView::paintTree"): return "paint"
    if (eventName == "LocalFrameView::performPreLayoutTasks"): return "stylelayout"
    if (eventName == "LocalFrameView::prePaint"): return "prepaint"
    if (eventName == "LocalFrameView::updateStyleAndLayoutIfNeededRecursive"): return "stylelayout"
    if (eventName == "LocalWindowProxy::CreateContext"): return "v8"
    if (eventName == "MessageLoop::RunTask"): return "scheduling"
    if (eventName == "MouseEventManager::handleMouseDraggedEvent"): return "events"
    if (eventName == "PageAnimator::serviceScriptedAnimations"): return "animations"
    if (eventName == "PaintArtifact::replay"): return "paint"
    if (eventName == "PaintController::commitNewDisplayItems"): return "paint"
    if (eventName == "PaintLayer::updateLayerPositionsAfterLayout"): return "compositing"
    if (eventName == "PaintLayer::updateScrollingStateAfterCompositingChange"): return "compositing"
    if (eventName == "PaintLayerCompositor::updateAfterCompositingChange"): return "compositing"
    if (eventName == "PaintLayerCompositor::updateIfNeededRecursive"): return "compositing"
    if (eventName == "ParseAuthorStyleSheet"): return "stylelayout"
    if (eventName == "ProxyMain::BeginMainFrame::commit"): return "cc"
    if (eventName == "Resource::appendData"): return "loading"
    if (eventName == "ResourceFetcher::requestResource"): return "loading"
    if (eventName == "RuleSet::addRulesFromSheet"): return "stylelayout"
    if (eventName == "ScheduledAction::execute"): return "v8"
    if (eventName == "StyleElement::processStyleSheet"): return "stylelayout"
    if (eventName == "StyleEngine::scheduleInvalidationsForRuleSets"): return "stylelayout"
    if (eventName == "StyleEngine::updateActiveStyleSheets"): return "stylelayout"
    if (eventName == "V8.DeoptimizeCode"): return "v8"
    if (eventName == "V8.GCFinalizeMC"): return "v8"
    if (eventName == "V8.GCIncrementalMarking"): return "v8"
    if (eventName == "V8.GCIncrementalMarkingFinalize"): return "v8"
    if (eventName == "V8.GCScavenger"): return "v8"
    if (eventName == "V8ContextSnapshot::InstallRuntimeEnabled"): return "v8"
    if (eventName == "WebLocalFrameImpl::createChildframe"): return "frames"
    if (eventName == "network.mojom.URLLoaderClient"): return "loading"
    if (eventName == "safe_browsing.mojom.PhishingModelSetter"): return "safebrowsing"
    if (eventName == "v8.callFunction"): return "v8"
    if (eventName == "v8.callModuleMethodSafe"): return "v8"
    if (eventName == "v8.run"): return "v8"
    return "unknown"

def analyze(traceFiles):
    events = []
    for traceFile in traceFiles:
        with open(traceFile) as f:
            traceJson = json.load(f)
        events.extend(rendererEvents(traceJson["traceEvents"]))

    categorySelfTimes = {}
    nameSelfTimes = {}
    totalSelfTime = 0;
    for event in events:
        name = event["name"]
        if not name in nameSelfTimes:
            nameSelfTimes[name] = 0
        nameSelfTimes[name] += event["self"]
        cat = category(name)
        if not cat in categorySelfTimes:
            categorySelfTimes[cat] = 0
        categorySelfTimes[cat] += event["self"]
        totalSelfTime += event["self"]

    print "self time by name:"
    sortedNameSelfTimes = sorted(nameSelfTimes.items(), key=operator.itemgetter(1))
    for name, time in sortedNameSelfTimes:
        print "  " + name + ", time: " + str(time) + " category: " + category(name) + " (" + str(100 * time / totalSelfTime) + "%)"

    print "self time by category:"
    sortedCategorySelfTimes = sorted(categorySelfTimes.items(), key=operator.itemgetter(1))
    for cat, time in sortedCategorySelfTimes:
        print "  " + cat + ", time: " + str(time) + " (" + str(100 * time / totalSelfTime) + "%)"

def main():
    parser = argparse.ArgumentParser(description="Analyze main thread time")
    parser.add_argument("traces", nargs="*", help="Traces to analyze, in json format")
    args, leftover = parser.parse_known_args()
    analyze(args.traces)

if __name__ == "__main__":
    main()
