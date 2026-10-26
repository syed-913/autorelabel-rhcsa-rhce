import assert from 'node:assert/strict';

export function assertInteractionReport(report){
  assert.equal(report.failure,undefined,'Keyboard walkthrough completed');
  assert.equal(report.menuKeyboard.open,true,'Enter opens the mobile navigation');
  assert.equal(report.distroKeyboard.selected,'tab-fedora','Arrow key selects the distribution');
  assert.equal(report.distroKeyboard.copied,true,'Enter copies the selected distribution commands');
  assert.equal(report.localSearchShortcut,true,'Slash focuses the task search');
  assert.equal(report.taskKeyboard.query,'?q=systemd','Search is reflected in the address');
  assert.equal(report.backPreservesFilter.value,'systemd','Back preserves the task filter');
  assert.deepEqual(report.backPreservesFilter.active,['Tasks'],'Back updates the active navigation');
  for(const state of [report.faqKeyboard,report.faqKeyboardReduced]){
    assert.equal(state.start,false);assert.equal(state.opened,true);assert.equal(state.closed,false);
    assert.equal(state.rapidClosed,true,'Rapid keyboard reversal settles closed');
  }
  assert.equal(report.faqKeyboardReduced.iconTransition,'0s','Reduced motion removes rotation');
  assert.equal(report.labs.length,4);
  for(const lab of report.labs){
    assert.equal(lab.enter.selected,'true');assert.equal(lab.space.selected,'true');
    assert.ok(lab.pageWidth<=lab.width,'The lab stays inside the page');
    assert.ok(lab.addressPixels>=14,'Lab addresses remain readable');
  }
  assert.equal(report.consoleKeyboard.status,'Relabelled. You can log in.','The keyboard console completes successfully');
  assert.match(report.consoleSkip,/Forgot touch/,'The missing marker produces the failure state');
  assert.match(report.clipboardFallback.selection,/^git clone /,'Clipboard failure selects the command');
  assert.equal(report.plainClick.pressed.visible,'false');
  assert.equal(report.plainClick.recovered.visible,'true');
  assert.equal(report.plainClick.recovered.pressed,false,'Click recovery clears the pressed state');
  assert.equal(report.offscreen.state,'paused','The score loop pauses offscreen');
}
