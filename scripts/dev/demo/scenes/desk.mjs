// The Exam Desk tour for the website, on a real lab: sign in with the code, read the first task,
// open node1's serial console and log in, look at its connections, then open SSH to node2 beside
// it. Run it with record-desk.sh, which starts the desk and passes the code in DESK_CODE and
// node1's console password in DESK_NODE1_PASSWORD.
export const width = 1600, height = 960, outWidth = 1280, scheme = 'dark';

const code = process.env.DESK_CODE || '';
const password = process.env.DESK_NODE1_PASSWORD || '';
const enter = (page) => page.key('Enter', 'Enter', 13);

async function typeLine(page, text, pause = 900) {
  await page.type(text, 45);
  await enter(page);
  await page.wait(pause);
}

export async function run(page, url) {
  await page.goto(url);
  await page.wait(900);
  await page.click('#code', 500);
  await page.type(code, 90);
  await page.wait(300);
  await page.click('#login-form button[type=submit]', 500);
  await page.wait(1800);                                   // the tasks, the nodes and the clock appear
  await page.moveTo('.task-num:nth-of-type(2)', 600);
  await page.click(null);
  await page.wait(1100);
  await page.click('.task-num:nth-of-type(1)', 500);
  await page.wait(1300);
  await page.click('#new-console', 700);                   // node1 has no network: the console it is
  await page.wait(2500);
  await enter(page);
  await page.wait(1500);
  await typeLine(page, 'root', 1200);
  await page.type(password, 30);
  await enter(page);
  await page.wait(2200);
  await typeLine(page, 'nmcli -g NAME,DEVICE connection show', 1600);
  await page.click('#mark-flag', 700);
  await page.wait(900);
  await page.click('#split', 700);
  await page.wait(500);
  await page.click('.node-tab:nth-of-type(2)', 700);      // node2: SSH works, and asks for root's password
  await page.wait(600);
  await page.click('#new-shell', 600);
  await page.wait(3200);
  await page.click('#mark-done', 700);
  await page.wait(1500);
  await page.moveTo('#end-exam', 900);
  await page.wait(1200);
}
