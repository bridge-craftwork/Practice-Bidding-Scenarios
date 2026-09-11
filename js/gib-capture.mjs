// GIB capture: have BBO's robots bid N deals from one dealer script, and log
// each auction as PBN. Driven by py/gib_capture.py - run that, not this.
//
// This is a test module for pbs-bbo-extension's test/playwright/pwrun.mjs, the
// live-BBO harness (hard watchdog, signed-in test profile, invisible sign-in).
// The job arrives as a JSON file named by $GIB_JOB:
//
//   { scenario, code, seat, boards, partialPbn, stallSeconds, delaySeconds, demo }
//
// The PBN is written to `partialPbn` every time a board arrives, so a watchdog
// timeout still leaves every board captured so far on disk.
//
// demo: stop once the table is up with the script loaded, capturing nothing,
// and hand it to a person (the driver runs the harness with --keep-open).
// Closing the BBO tab ends the harness.
//
// Capture is the BBOalert PBNcapture plugin, which -PBS.txt loads. It logs each
// finished auction to localStorage.PBNcapture and clicks Redeal. Its settings
// live in a closure, but addConfigBox() hangs that same object off its entry in
// the config menu (option.cfgObj), so it can be switched on and off in place
// without touching the plugin's saved settings.
import { readFileSync, writeFileSync } from 'fs';

const BBO_URL = 'https://www.bridgebase.com/v3/app/lv';
const CAPTURE_LABEL = 'PBN capture and auto-redeal';

export default async function ({ page, ctx, say }) {
  const job = JSON.parse(readFileSync(process.env.GIB_JOB, 'utf8'));
  const t0 = Date.now();
  const secs = () => Math.round((Date.now() - t0) / 1000);
  const out = { scenario: job.scenario, requested: job.boards, captured: 0, status: 'started' };
  // say() only reaches the result file; the driver also wants progress live.
  const note = m => { say(m); console.log(`[gib ${secs()}s] ${m}`); };

  const pbsLog = [];
  page.on('console', m => { const t = m.text(); if (t.startsWith('[PBS]')) pbsLog.push(t); });

  // Run fn inside the PBS iframe, where setDealerCode, startTable and the
  // BBOalert config menu live. fn is serialised, so it sees only its argument.
  const inPbs = async (fn, arg) => {
    const frame = await (await page.$('#pbs-iframe'))?.contentFrame();
    if (!frame) throw new Error('no PBS iframe');
    return frame.evaluate(fn, arg);
  };

  const waitUntil = async (what, test, seconds) => {
    for (let i = 0; i < seconds; i++) {
      if (await test().catch(() => false)) return;
      await page.waitForTimeout(1000);
    }
    throw new Error(`timed out after ${seconds}s waiting for ${what}`);
  };

  const readLog = () => page.evaluate(() => localStorage.getItem('PBNcapture') || '');
  const records = log => log.split(/\n(?=\[Event )/).map(r => r.trim()).filter(r => r.startsWith('[Event '));
  const boardOf = rec => parseInt((rec.match(/^\[Board "(\d+)"\]/m) || [])[1], 10) || 0;

  const setCapture = (enable, redeals) => inPbs(a => {
    const sel = document.getElementById('bboalert-menu-config');
    const opt = sel && [...sel.options].find(o => o.cfgLabel === a.label);
    if (!opt) return false;
    opt.cfgObj.Enable_Log = a.enable;
    opt.cfgObj.Auto_redeals = a.redeals;
    return true;
  }, { label: CAPTURE_LABEL, enable, redeals });

  // Start from an empty capture log, keeping the old one to put back at the end.
  // The plugin reads the log into memory when it loads, hence the reload.
  await page.goto(BBO_URL, { waitUntil: 'domcontentloaded' });
  let savedLog = null;
  if (!job.demo) {
    savedLog = await page.evaluate(() => {
      const v = localStorage.getItem('PBNcapture');
      localStorage.setItem('PBNcapture', '');
      return v;
    });
    await page.reload({ waitUntil: 'domcontentloaded' });
  }

  try {
    await waitUntil('the PBS panel, with PBNcapture loaded', () => inPbs(label => {
      const sel = document.getElementById('bboalert-menu-config');
      return typeof setDealerCode === 'function' && typeof startTable === 'function' &&
        !!sel && [...sel.options].some(o => o.cfgLabel === label);
    }, CAPTURE_LABEL), 90);
    note('PBS panel ready');

    // startTable() seats the host South and robots in the other three. For a
    // robots-only auction South must be a robot too, and the host's own seat
    // menu offers [Sit, Robot, Reserve] - so reuse the loaded startTable with
    // that one choice changed, rather than a copy that would drift from it.
    const patched = await inPbs(() => {
      const src = startTable.toString();
      const robots = src.replace('seatOne(0, "Sit")', 'seatOne(0, "Robot")');
      if (robots === src) return false;
      window.eval('window.gibStartTable = ' + robots);
      return true;
    });
    if (!patched) throw new Error('startTable no longer contains seatOne(0, "Sit") - update gib-capture.mjs');
    await inPbs(() => gibStartTable('bidding'));

    // Assert the seats, not the DONE line: an empty seat looks like "South".
    out.seats = await page.evaluate(() =>
      [...document.querySelectorAll('bridge-screen .nameDisplayClass')].map(n => n.textContent.trim()));
    note('seats: ' + JSON.stringify(out.seats));
    if (out.seats.length !== 4 || out.seats.some(s => !s || /^(North|South|East|West)\b/.test(s))) {
      throw new Error('table did not fill with four robots: ' + JSON.stringify(out.seats) +
                      ' / ' + JSON.stringify(pbsLog.slice(-5)));
    }

    // Rotation off, so the dealer and seats are the script's own. The rotate
    // argument only applies when no preference is stored, so hide the stored
    // one for this call. setDealerCode redeals when it is done.
    //
    // The table's first deal predates the script and may still be being bid
    // when capture starts, so its auction would be logged too. Board numbers
    // only climb at a table: note the current one, and keep only later boards.
    const scriptlessBoard = parseInt(await inPbs(() => getDealNumber()), 10) || 0;
    const done = pbsLog.length;
    await inPbs(a => {
      const pref = pbsGetRotatePref;
      window.pbsGetRotatePref = () => null;
      try { setDealerCode(a.code, a.seat, false); } finally { window.pbsGetRotatePref = pref; }
    }, { code: job.code, seat: job.seat });
    await waitUntil('setDealerCode to finish',
      async () => pbsLog.slice(done).some(l => l.includes('setDealerCode DONE')), 30);
    note('dealer script set, dealer ' + job.seat + ', rotation off');

    if (job.demo) {
      page.on('close', () => process.exit(0));
      ctx.on('close', () => process.exit(0));
      out.status = 'demo';
      out.elapsedSec = secs();
      note('demo table ready: Redeal for new deals; close the BBO tab when done');
      return out;
    }

    // Every deal from here on comes from the script. Without a delay the plugin
    // redeals the moment an auction ends, and Auto_redeals is only a ceiling (a
    // manual redeal below also counts against it); the loop stops capture
    // itself at N. With a delay the plugin must not redeal at all - the loop
    // does it, after the pause.
    const delayMs = (job.delaySeconds || 0) * 1000;
    const redeal = () => page.evaluate(() => document.querySelector('.redeal-button')?.click());
    if (!await setCapture(true, delayMs ? 0 : job.boards * 2 + 20)) throw new Error('PBNcapture config not found');
    await redeal();

    let have = 0, lastProgress = Date.now(), kicks = 0;
    out.redealKicks = 0;
    while (have < job.boards) {
      await page.waitForTimeout(1000);
      const all = records(await readLog());
      const recs = all.filter(r => boardOf(r) > scriptlessBoard);
      out.discarded = all.length - recs.length;
      if (recs.length > have) {
        have = recs.length;
        kicks = 0;
        writeFileSync(job.partialPbn, recs.slice(0, job.boards).join('\n\n') + '\n');
        if (have % 10 === 0 || have >= job.boards) note(`${Math.min(have, job.boards)}/${job.boards} boards`);
        if (delayMs && have < job.boards) {
          await page.waitForTimeout(delayMs);
          await redeal();
        }
        lastProgress = Date.now();
      } else if (Date.now() - lastProgress > job.stallSeconds * 1000) {
        // An auction that never ends, or a redeal that did not take.
        if (++kicks > 3) { out.status = 'stalled'; break; }
        out.redealKicks++;
        note(`no board for ${job.stallSeconds}s - clicking Redeal (${kicks}/3)`);
        await redeal();
        lastProgress = Date.now();
      }
    }
    out.captured = Math.min(have, job.boards);
    if (out.status !== 'stalled') out.status = 'ok';
  } catch (e) {
    out.status = 'error';
    out.error = String(e?.message || e);
    note('ERROR: ' + out.error);
  } finally {
    // Leave BBO as it was found: capture off, the old log back. The robots'
    // table ends when the browser closes. A demo never touched either.
    if (!job.demo) {
      await setCapture(false, 0).catch(() => {});
      await page.evaluate(v => {
        if (v === null) localStorage.removeItem('PBNcapture'); else localStorage.setItem('PBNcapture', v);
      }, savedLog).catch(() => {});
    }
  }

  out.elapsedSec = secs();
  out.pbsLog = pbsLog.slice(-20);
  note(`${out.status}: ${out.captured}/${job.boards} boards in ${out.elapsedSec}s`);
  return out;
}
