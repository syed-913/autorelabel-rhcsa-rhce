// The results dashboard tour for the website: the overview's chart, the weak spots, an objective,
// a task's checks and one attempt. Run it with record.mjs against a dashboard serving the
// made-up workspace of results_demo.py, with the launch address as the url.
export const width = 1440, height = 900, outWidth = 1280, scheme = 'dark';

export async function run(page, url) {
  await page.goto(url);
  await page.wait(2600);                                   // the hairline, the tiles and the chart draw in
  for (const n of [2, 5, 8, 10]) {
    await page.moveTo(`.chart a.pt:nth-of-type(${n}) .shape`, 650);
    await page.wait(900);
  }
  await page.scrollTo('.cols', 1100);
  await page.wait(500);
  await page.moveTo('.cols section:first-child .item:nth-of-type(1) .head a', 700);
  await page.wait(700);
  await page.moveTo('.cols section:last-child .item:nth-of-type(1)', 700);
  await page.wait(800);
  await page.click('.cols section:first-child .item:nth-of-type(1) .head a', 600);
  await page.wait(2200);                                   // the objectives page, scrolled to that line
  await page.click('.pages a:nth-of-type(3)', 900);
  await page.wait(1800);
  await page.moveTo('details.task:nth-of-type(3) summary', 700);
  await page.wait(400);
  await page.click(null);
  await page.wait(1500);
  await page.click('.pages a:nth-of-type(1)', 900);
  await page.wait(1200);
  await page.scrollTo('.table-wrap', 1200, 140);
  await page.moveTo('tbody tr:nth-child(1) .open', 800);
  await page.wait(500);
  await page.click(null);
  await page.wait(2600);                                   // the attempt: the score bar grows
  await page.scrollTo('section:last-of-type', 1300);
  await page.moveTo('details.task:nth-of-type(4) summary', 700);
  await page.click(null);
  await page.wait(2200);
}
