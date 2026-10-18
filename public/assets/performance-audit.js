/* Opt-in browser cadence audit: ?i3-audit=1. No sensor or rendering changes. */
(() => {
  if (!new URLSearchParams(location.search).has('i3-audit')) return;
  let last = 0, start = 0, gaps = [], longTasks = 0, path = '', size = '';
  try { new PerformanceObserver(list => { longTasks += list.getEntries().length; }).observe({type:'longtask', buffered:false}); } catch (_) {}
  function sample(now) {
    requestAnimationFrame(sample);
    const nextSize = `${innerWidth}x${innerHeight}@${devicePixelRatio}`;
    if (document.hidden || path !== location.pathname || size !== nextSize || !document.documentElement.dataset.i3Ready) {
      last = start = 0; gaps = []; longTasks = 0; path = location.pathname; size = nextSize; return;
    }
    if (!start) start = now;
    if (last) gaps.push(now - last);
    last = now;
    if (now - start < 10000) return;
    const sorted = gaps.slice().sort((a,b) => a-b);
    document.documentElement.dataset.i3Audit = JSON.stringify({path, size, seconds:(now-start)/1000,
      frames:gaps.length, callbackHz:gaps.length*1000/(now-start), median:sorted[Math.floor(sorted.length*.5)],
      p95:sorted[Math.floor(sorted.length*.95)], max:sorted[sorted.length-1], over20:gaps.filter(x=>x>20).length, longTasks});
    start = now; gaps = []; longTasks = 0;
  }
  requestAnimationFrame(sample);
})();
