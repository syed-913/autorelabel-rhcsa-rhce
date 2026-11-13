// What's new, with its recorded tour: shown in the home page's hero and tour section and at the top
// of the changelog. The newest feature goes first; a release with a new tour adds one entry here.
export interface Feature {
  version: string;
  id: string;
  name: string;
  heading: [string, string];
  lede: [string, string];
  frame: [string, string];
  media: {webm: string; mp4: string; poster: string; label: string; description: string};
  points: [string, string][];
  how: string;
  guide: [string, string];
}

export const features: Feature[] = [
  {
    version: '1.3.0',
    id: 'results',
    name: 'the results dashboard',
    heading: ['See where', 'your points go.'],
    lede: ['The results dashboard, new in 1.3.0.', 'In your browser, on your own computer.'],
    frame: ['autorelabel dashboard', '127.0.0.1'],
    media: {
      webm: '/media/results-dashboard.webm', mp4: '/media/results-dashboard.mp4', poster: '/media/results-dashboard-poster.webp',
      label: 'A tour of the results dashboard, with made-up results',
      description: 'A recording of the results dashboard with made-up attempts: the scores chart with a result’s details on hover, the objectives that cost the most points, the checks failed more than once, the tasks with their checks, and one attempt’s report.',
    },
    points: [
      ['Scores over time.', 'Every attempt against the pass mark. Point at one to see it, and open its full report.'],
      ['What keeps costing you points.', 'Every objective with your share of its points and which way it is going.'],
      ['Before and after the reboot.', 'Each check of each attempt, with the answers that worked until the grading reboot marked.'],
    ],
    how: 'Run <code>./autorelabel dashboard</code>, or press <kbd>o</kbd> on <strong>Progress and history</strong>. It reads the results autorelabel already keeps. It changes nothing and sends nothing anywhere.',
    guide: ['Grading and results ↗', '/docs/grading-and-results/'],
  },
];

export const latest = features[0];
