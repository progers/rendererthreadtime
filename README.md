Analyze renderer thread time
=========

This is a basic tool for understanding where the Chromium renderer threads are spending their time. This categorizes and sorts trace events by self-time.

Basic usage: `analyze.py trace_file.json`

Run tests: `python -m unittest discover`

Steps:
1. Navigate to chrome://tracing, record a trace with the categories: blink, cc, gpu, loading, mojom, toplevel, v8
2. In a new tab, navigate to some page.
3. In chrome://tracing, stop tracing and save the trace.
4. Uncompress the trace file with "gunzip [trace_file.json].gz".
5. Repeat steps 1-5 for many pages.
6. Run `analyze.py trace_file_1.json trace_file_2.json ...`

Example output:
```
Self time by category:
  hittest, self time: 5ms (0.0% of total time)
  frames, self time: 43ms (0.1% of total time)
  rootscroller, self time: 43ms (0.1% of total time)
  script, self time: 72ms (0.2% of total time)
  gpu, self time: 77ms (0.2% of total time)
  intersectionobserver, self time: 94ms (0.2% of total time)
  parsing, self time: 119ms (0.3% of total time)
  unknown timer, self time: 252ms (0.7% of total time)
  animations, self time: 306ms (0.8% of total time)
  parser, self time: 363ms (1.0% of total time)
  prepaint, self time: 390ms (1.0% of total time)
  events, self time: 659ms (1.7% of total time)
  loading, self time: 1462ms (3.9% of total time)
  paint, self time: 1530ms (4.0% of total time)
  cc, self time: 1670ms (4.4% of total time)
  scheduling, self time: 1690ms (4.5% of total time)
  unknown, self time: 2288ms (6.0% of total time)
  compositing, self time: 2618ms (6.9% of total time)
  unknown task, self time: 4267ms (11.3% of total time)
  stylelayout, self time: 5728ms (15.1% of total time)
  v8, self time: 14156ms (37.4% of total time)
Total self time: 37842ms from 395684 events
```
