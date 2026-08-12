import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

async function render() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(new Request("http://localhost/", { headers: { accept: "text/html" } }), {
    ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) },
  }, { waitUntil() {}, passThroughOnException() {} });
}

test("server-renders the evaluation dashboard", async () => {
  const response = await render();
  assert.equal(response.status, 200);
  assert.match(response.headers.get("content-type") ?? "", /^text\/html\b/i);
  const html = await response.text();
  assert.match(html, /<title>RAG Evaluation Lab/);
  assert.match(html, /One dataset/);
  assert.match(html, /151/);
  assert.match(html, /Case matrix/);
  assert.match(html, /Trace inspector/);
  assert.match(html, /Complete with limitations/);
  assert.doesNotMatch(html, /codex-preview|react-loading-skeleton|Starter Project/);
});

test("source includes all interactive evidence flows", async () => {
  const [page, css, layout] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
    readFile(new URL("../app/layout.tsx", import.meta.url), "utf8"),
  ]);
  assert.match(page, /const cases: Case\[\] = \[/);
  assert.equal((page.match(/\{id:"[EMHA]\d\d"/g) ?? []).length, 20);
  assert.match(page, /setMetricIndex/);
  assert.match(page, /setFilter/);
  assert.match(page, /setSelectedId/);
  assert.match(page, /Provider limitation/);
  assert.match(css, /@media\(max-width:850px\)/);
  assert.match(css, /@media\(max-width:520px\)/);
  assert.match(layout, /RAGAS vs DeepEval/);
});
