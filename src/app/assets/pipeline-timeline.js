(() => {
  'use strict';
  const section = document.getElementById('how');
  const home = document.getElementById('home-view');
  if (!section || !home || !window.gsap || !window.ScrollTrigger || !window.SplitText) return;
  gsap.registerPlugin(ScrollTrigger, SplitText);
  const viewport = section.querySelector('.pipeline-viewport');
  const track = section.querySelector('.pipeline-track');
  const milestones = section.querySelector('.pipeline-milestones');
  const steps = [...section.querySelectorAll('.pipeline-step')];
  const buttons = [...section.querySelectorAll('[data-pipeline-step]')];
  const previous = document.getElementById('pipeline-prev');
  const next = document.getElementById('pipeline-next');
  const compact = matchMedia('(max-width: 479px), (max-height: 439px), (prefers-reduced-motion: reduce)');
  let context = null;
  let panTrigger = null;
  let splits = [];
  let active = -1;
  let running = false;

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
    splits.forEach(split => split.revert());
    context = null;
    splits = [];
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
      const distance = () => Math.max(0, track.scrollWidth - viewport.clientWidth);
      const pan = gsap.to(track, {
        x: () => -distance(), ease: 'none',
        scrollTrigger: {
          trigger: viewport, start: 'top top', end: () => `+=${distance()}`,
          pin: true, scrub: 0.7, anticipatePin: 1, invalidateOnRefresh: true,
          onUpdate: self => activate(Math.min(steps.length - 1, Math.round(self.progress * (steps.length - 1))))
        }
      });
      panTrigger = pan.scrollTrigger;
      gsap.fromTo(milestones, { '--pipeline-progress': 0.05 }, {
        '--pipeline-progress': 1, ease: 'none',
        scrollTrigger: { trigger: viewport, start: 'top top', end: () => `+=${distance()}`, scrub: 0.7 }
      });
      steps.forEach(step => {
        const split = new SplitText(step.querySelector('p'), { type: 'lines', mask: 'lines' });
        splits.push(split);
        gsap.timeline({ scrollTrigger: { trigger: step, containerAnimation: pan, start: 'left 95%', end: 'left 60%', scrub: true } })
          .from(step.querySelector('.pipeline-stem'), { scaleY: 0, duration: 0.42 })
          .from(step.querySelector('.pipeline-dot'), { scale: 0, duration: 0.42 }, '<')
          .from(step.querySelector('h3'), { y: 20, opacity: 0, duration: 1.4 }, '<')
          .from(split.lines, { yPercent: 100, duration: 1.4, stagger: 0.07 }, '<');
      });
    }, section);
    ScrollTrigger.refresh();
  }
  function goTo(index) {
    if (!panTrigger) return;
    const bounded = Math.max(0, Math.min(steps.length - 1, index));
    window.scrollTo({ top: panTrigger.start + bounded / (steps.length - 1) * (panTrigger.end - panTrigger.start), behavior: 'instant' });
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
