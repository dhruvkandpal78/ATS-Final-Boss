(() => {
  'use strict';
  const section = document.getElementById('how');
  const home = document.getElementById('home-view');
  if (!section || !home || !window.gsap || !window.ScrollTrigger) return;
  gsap.registerPlugin(ScrollTrigger);
  const viewport = section.querySelector('.pipeline-viewport');
  const track = section.querySelector('.pipeline-track');
  const milestones = section.querySelector('.pipeline-milestones');
  const steps = [...section.querySelectorAll('.pipeline-step')];
  const buttons = [...section.querySelectorAll('[data-pipeline-step]')];
  const previous = document.getElementById('pipeline-prev');
  const next = document.getElementById('pipeline-next');
  const compact = matchMedia('(max-width: 479px), (max-height: 599px), (prefers-reduced-motion: reduce)');
  let context = null;
  let panTrigger = null;
  let pan = null;
  let targets = [];
  let active = -1;
  let running = false;

  function readingPoint() {
    // The first step must be reachable even when a wide viewport shows the cover.
    return Math.min(viewport.clientWidth * 0.35,
      milestones.offsetLeft + steps[0].offsetLeft);
  }

  // All visual states follow the rendered pan, including its scrub easing.
  function measure() {
    const inset = parseFloat(getComputedStyle(track).paddingRight) || 0;
    const focus = readingPoint();
    const last = steps[steps.length - 1];
    const tail = Math.max(0, viewport.clientWidth - focus - last.offsetWidth - inset);
    milestones.style.setProperty('--pipeline-tail', `${tail}px`);
    milestones.style.setProperty('--pipeline-line-end', `${last.offsetWidth + tail}px`);
    const distance = Math.max(0, track.scrollWidth - viewport.clientWidth);
    targets = steps.map(step => Math.max(0, Math.min(distance,
      milestones.offsetLeft + step.offsetLeft - focus)));
    return distance;
  }
  function render() {
    const x = Number(gsap.getProperty(track, 'x')) || 0;
    const focus = readingPoint();
    const first = milestones.offsetLeft + steps[0].offsetLeft;
    const last = milestones.offsetLeft + steps[steps.length - 1].offsetLeft;
    const position = focus - x;
    const fill = Math.max(0, Math.min(1, (position - first) / Math.max(1, last - first)));
    milestones.style.setProperty('--pipeline-progress', fill);
    let reachedStep = 0;
    steps.forEach((step, index) => {
      const node = milestones.offsetLeft + step.offsetLeft;
      // Entering the viewport is not reaching the milestone: reveal only when
      // the rendered progress line arrives at this dot (allow subpixel rounding).
      const reveal = position >= node - 0.5 ? 1 : 0;
      if (reveal) reachedStep = index;
      gsap.set(step.querySelector('.pipeline-stem'), { scaleY: reveal });
      gsap.set(step.querySelector('.pipeline-dot'), { scale: reveal });
      gsap.set(step.querySelector('.pipeline-copy'), { opacity: reveal, y: (1 - reveal) * 16 });
    });
    activate(reachedStep);
  }

  function activate(index) {
    if (index === active) return;
    active = index;
    buttons.forEach((button, position) => {
      button.classList.toggle('active', position === index);
      if (position === index) button.setAttribute('aria-current', 'step');
      else button.removeAttribute('aria-current');
    });
    previous.disabled = index <= 0;
    next.disabled = index >= steps.length - 1;
  }
  function teardown() {
    context?.revert();
    steps.forEach(step => {
      gsap.set(step.querySelector('.pipeline-copy'), { clearProps: 'opacity,transform' });
      gsap.set([step.querySelector('.pipeline-stem'), step.querySelector('.pipeline-dot')], { clearProps: 'transform' });
    });
    context = null;
    pan = null;
    targets = [];
    milestones.style.removeProperty('--pipeline-tail');
    milestones.style.removeProperty('--pipeline-line-end');
    milestones.style.removeProperty('--pipeline-progress');
    panTrigger = null;
    running = false;
    section.classList.add('pipeline-static');
  }
  function sync() {
    const shouldRun = !home.hidden && !compact.matches;
    if (shouldRun === running) return;
    if (!shouldRun) { teardown(); return; }
    running = true;
    section.classList.remove('pipeline-static');
    activate(0);
    context = gsap.context(() => {
      measure();
      pan = gsap.to(track, {
        x: () => -measure(), ease: 'none', onUpdate: render,
        scrollTrigger: {
          trigger: viewport, start: 'top top', end: () => `+=${measure()}`,
          pin: true, scrub: 0.7, anticipatePin: 1, invalidateOnRefresh: true,
          onRefresh: render
        }
      });
      panTrigger = pan.scrollTrigger;
      render();
    }, section);
    ScrollTrigger.refresh();
  }
  function goTo(index) {
    if (!panTrigger) return;
    ScrollTrigger.refresh();
    const bounded = Math.max(0, Math.min(steps.length - 1, index));
    const distance = measure();
    const progress = targets[bounded] / Math.max(1, distance);
    window.scrollTo({ top: panTrigger.start + progress * (panTrigger.end - panTrigger.start), behavior: 'instant' });
    ScrollTrigger.update();
    // Button navigation settles immediately; free scrolling keeps the scrub.
    panTrigger.getTween()?.progress(1);
    pan.progress(progress);
    render();
  }
  buttons.forEach(button => button.addEventListener('click', () => goTo(Number(button.dataset.pipelineStep))));
  previous.addEventListener('click', () => goTo(active - 1));
  next.addEventListener('click', () => goTo(active + 1));
  compact.addEventListener('change', sync);
  document.addEventListener('ats:routechange', sync);
  const observer = new MutationObserver(sync);
  observer.observe(home, { attributes: true, attributeFilter: ['hidden'] });
  window.addEventListener('pagehide', () => { observer.disconnect(); teardown(); });
  sync();
  void document.fonts.ready.then(() => { if (running) ScrollTrigger.refresh(); });
})();
