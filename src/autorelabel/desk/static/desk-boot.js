// Runs before xterm.js. The page's Content-Security-Policy allows <style> elements only with this
// response's nonce, and xterm.js writes its own <style> elements (its renderer's sizes and colours)
// with no nonce option. So every <style> created by a script gets the nonce this script tag carries.
// An injected <style> in markup has no nonce and stays blocked. xterm.js itself is left unmodified.
(() => {
  const nonce = document.currentScript && document.currentScript.nonce;
  if (!nonce) return;
  const create = Document.prototype.createElement;
  Document.prototype.createElement = function (name, options) {
    const element = create.call(this, name, options);
    if (String(name).toLowerCase() === 'style') element.nonce = nonce;
    return element;
  };
})();
