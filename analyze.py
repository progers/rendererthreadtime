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
# time spent in all other events occurring at the same time. For example:
#         [               a: self=3               ]
#              [  b: self=1   ]    [d: self=2]
#                   [c: self=2]
#
#   time: 0    1    2    3    4    5    6    7    8    9
def _computeThreadSelfTimes(events):
    # This algorithm iterates through the events in order of begin time and
    # keeps track of the current stack. An assumption is that all events are
    # from a single thread and are nicely nested (i.e., no events overlap like
    # [begin:1, end:4] and [begin:3, end:5]). There are two important steps:
    # 1) When an event is pushed, the self time is set to the event's duration.
    # 2) After an event is popped, the event's duration is subtracted from the
    #    enclosing event's self time.
    # The first step computes the self time for "leaf" events and the second
    # step recursively updates self time for nested events.
    events.sort(key=lambda event: event["begin"])
    stack = []

    def duration(event):
        return event["end"] - event["begin"]
    def push(event):
        event["self"] = duration(event)
        stack.append(event)
    def pop():
        event = stack.pop()
        if stack:
            stack[-1]["self"] -= duration(event)
    def nested(outer, inner):
        return outer["begin"] <= inner["begin"] and outer["end"] >= inner["end"]

    for event in events:
        while stack and not nested(stack[-1], event):
            pop()
        push(event)
    while stack:
        pop()

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
        _computeThreadSelfTimes(eventsById[id])

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

    if (eventName == "BackgroundHTMLParser::pumpTokenizer"): return "parser"
    if (eventName == "BackgroundHTMLParser::sendTokensToMainThread"): return "parser"
    if (eventName == "CommandBufferProxyImpl::Initialize"): return "gpu"
    if (eventName == "CompositingInputsUpdater::update"): return "compositing"
    if (eventName == "CompositingLayerAssigner::assign"): return "compositing"
    if (eventName == "CompositingRequirementsUpdater::updateRecursive"): return "compositing"
    if (eventName == "ContextCreatedNotification"): return "v8"
    if (eventName == "DisplayItemList::Finalize"): return "paint"
    if (eventName == "Document::rebuildLayoutTree"): return "layout"
    if (eventName == "Document::recalcStyle"): return "style"
    if (eventName == "Document::updateActiveStyle"): return "style"
    if (eventName == "Document::updateStyleInvalidationIfNeeded"): return "style"
    if (eventName == "DocumentTimeline::serviceAnimations"): return "animations"
    if (eventName == "EventHandler::HitTestResultAtLocation"): return "hittest"
    if (eventName == "EventHandler::handleMouseMoveEvent"): return "events"
    if (eventName == "GraphicsLayer::PaintContents"): return "paint"
    if (eventName == "GraphicsLayerTreeBuilder::rebuild"): return "compositing"
    if (eventName == "GraphicsLayerUpdater::update"): return "compositing"
    if (eventName == "HTMLDocumentParser::EnqueueTokenizedChunk"): return "parser"
    if (eventName == "HTMLDocumentParser::processTokenizedChunkFromBackgroundParser"): return "parser"
    if (eventName == "HTMLParserScriptRunner ExecuteScript"): return "script"
    if (eventName == "HTMLParserScriptRunner::execute"): return "v8"
    if (eventName == "ImageResourceContent::updateImage"): return "loading"
    if (eventName == "IntersectionObserverController::computeTrackedIntersectionObservations"): return "intersectionobserver"
    if (eventName == "LayerTreeHost::DoUpdateLayers"): return "cc"
    if (eventName == "LayerTreeHost::UpdateLayers::BuildPropertyTrees"): return "cc"
    if (eventName == "LocalFrameView::UpdateViewportIntersectionsForSubtree"): return "intersectionobserver"
    if (eventName == "LocalFrameView::layout"): return "layout"
    if (eventName == "LocalFrameView::paintTree"): return "paint"
    if (eventName == "LocalFrameView::performPreLayoutTasks"): return "layout"
    if (eventName == "LocalFrameView::prePaint"): return "prepaint"
    if (eventName == "LocalFrameView::updateStyleAndLayoutIfNeededRecursive"): return "layout"
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
    if (eventName == "ParseAuthorStyleSheet"): return "style"
    if (eventName == "ProxyMain::BeginMainFrame::commit"): return "cc"
    if (eventName == "Resource::appendData"): return "loading"
    if (eventName == "ResourceFetcher::requestResource"): return "loading"
    if (eventName == "ResourceLoadPriorityOptimizer::updateAllImageResourcePriorities"): return "loading"
    if (eventName == "RootScrollerController::PerformRootScrollerSelection"): return "rootscroller"
    if (eventName == "RuleSet::addRulesFromSheet"): return "style"
    if (eventName == "ScheduledAction::execute"): return "v8"
    if (eventName == "SequenceManager.DidProcessTaskObservers"): return "sequencemanager"
    if (eventName == "SequenceManager.DidProcessTaskTimeObservers"): return "sequencemanager"
    if (eventName == "SequenceManager.QueueNotifyDidProcessTask"): return "sequencemanager"
    if (eventName == "SequenceManager.QueueNotifyWillProcessTask"): return "sequencemanager"
    if (eventName == "SequenceManager.QueueOnTaskCompleted"): return "sequencemanager"
    if (eventName == "SequenceManager.QueueOnTaskStarted"): return "sequencemanager"
    if (eventName == "SequenceManager.WillProcessTaskObservers"): return "sequencemanager"
    if (eventName == "SequenceManager.WillProcessTaskTimeObservers"): return "sequencemanager"
    if (eventName == "SequenceManagerImpl::NotifyDidProcessTaskObservers"): return "sequencemanager"
    if (eventName == "SequenceManagerImpl::NotifyWillProcessTaskObservers"): return "sequencemanager"
    if (eventName == "SequenceManagerImpl::WakeUpReadyDelayedQueues"): return "sequencemanager"
    if (eventName == "StyleElement::processStyleSheet"): return "style"
    if (eventName == "StyleEngine::scheduleInvalidationsForRuleSets"): return "style"
    if (eventName == "StyleEngine::updateActiveStyleSheets"): return "style"
    if (eventName == "ThreadControllerImpl::ScheduleWork::PostTask"): return "scheduler"
    if (eventName == "V8.DeoptimizeCode"): return "v8"
    if (eventName == "V8.GCFinalizeMC"): return "v8"
    if (eventName == "V8.GCFinalizeMCReduceMemory"): return "v8"
    if (eventName == "V8.GCIncrementalMarking"): return "v8"
    if (eventName == "V8.GCIncrementalMarkingFinalize"): return "v8"
    if (eventName == "V8.GCIncrementalMarkingStart"): return "v8"
    if (eventName == "V8.GCScavenger"): return "v8"
    if (eventName == "V8ContextSnapshot::InstallRuntimeEnabled"): return "v8"
    if (eventName == "WebLocalFrameImpl::createChildframe"): return "frames"
    if (eventName == "WebURLLoaderImpl::Context::Cancel"): return "loading"
    if (eventName == "WebURLLoaderImpl::Context::OnCompletedRequest"): return "loading"
    if (eventName == "WebURLLoaderImpl::Context::OnReceivedResponse"): return "loading"
    if (eventName == "WebURLLoaderImpl::Context::Start"): return "loading"
    if (eventName == "WebURLLoaderImpl::loadAsynchronously"): return "loading"
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
    totalSelfTime = 0
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

    out = []
    out.append("Self time by name:")
    sortedNameSelfTimes = sorted(nameSelfTimes.items(), key=operator.itemgetter(1))
    for name, time in sortedNameSelfTimes:
        out.append("  {0}, category: {1}, self time: {2}ms ({3:03.1f}% of total time)".format(name, category(name), time / 1000, 100.0 * time / totalSelfTime))

    out.append("Self time by category:")
    sortedCategorySelfTimes = sorted(categorySelfTimes.items(), key=operator.itemgetter(1))
    for cat, time in sortedCategorySelfTimes:
        out.append("  {0}, self time: {1}ms ({2:03.1f}% of total time)".format(cat, time / 1000, 100.0 * time / totalSelfTime))

    out.append("Total self time: {0}ms from {1} events".format(totalSelfTime / 1000, len(events)))
    return "\n".join(out)

def main():
    parser = argparse.ArgumentParser(description="Analyze renderer thread time")
    parser.add_argument("traces", nargs="*", help="Traces to analyze, in json format")
    args, leftover = parser.parse_known_args()
    print analyze(args.traces)

if __name__ == "__main__":
    main()
