export const base = '/autorelabel-rhcsa-rhce';
export const repository = 'https://github.com/syed-913/autorelabel-rhcsa-rhce';
export const href = (path = '/') => `${base}/${path.replace(/^\/+/, '')}`;
export const canonical = (path = '/') => `https://syed-913.github.io${href(path)}`;

const guideSlugs: Record<string, string> = {
  '01-installing': 'installing', '02-first-exam': 'first-exam',
  '03-exam-screen': 'exam-screen', '04-the-lab': 'the-lab',
  '05-grading-and-results': 'grading-and-results', '06-practice': 'practice',
  '07-commands': 'commands', '08-settings': 'settings',
  '09-troubleshooting': 'troubleshooting', '10-files-and-uninstall': 'files-and-uninstall',
  '12-objectives': 'objectives',
};
export const guideSlug = (file: string) => guideSlugs[file.replace(/\.md$/, '')] || file.replace(/^\d+-/, '').replace(/\.md$/, '');

export function sourceLink(raw: string, source: string): string {
  if (/^(https?:|mailto:|tel:)/.test(raw)) return raw;
  if (raw.startsWith('#')) return raw;
  const [file, fragment] = raw.split('#');
  const parts = source.split('/').slice(0, -1);
  for (const part of file.split('/')) {
    if (part === '..') parts.pop();
    else if (part && part !== '.') parts.push(part);
  }
  const path = parts.join('/');
  const hash = fragment ? `#${fragment}` : '';
  if (path === 'README.md') {
    const anchors: Record<string, string> = {
      'quick-start': '/start/#getting-started', 'getting-started': '/start/#getting-started',
      requirements: '/start/#requirements', 'supported-hosts': '/#platforms',
      'supported-platforms': '/#platforms', faq: '/faq/',
      'what-the-rhcsa-lab-looks-like': '/rhcsa/#lab',
      'what-the-rhce-lab-looks-like': '/rhce/#lab',
      'how-it-compares': '/#comparison', license: '/#licence',
    };
    return href(anchors[fragment || ''] || (fragment ? `/start/${hash}` : '/'));
  }
  if (path === 'docs/guide/README.md') return href(`/docs/${hash}`);
  if (path === 'docs/guide/11-faq.md') return href(`/faq/${hash}`);
  if (path.startsWith('docs/guide/') && path.endsWith('.md')) return href(`/docs/${guideSlug(path.split('/').pop()!)}/${hash}`);
  return `${repository}/blob/main/${path}${hash}`;
}
