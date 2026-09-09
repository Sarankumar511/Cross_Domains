// Package the built SPA (dist/*) flat into mta-dist/bridgescout.zip so the
// HTML5 Application Repository sees one app zip with manifest.json at its root.
// Uses adm-zip (no transitive deps) - bestzip's archiver tree breaks on Node 24.
import { mkdirSync, rmSync } from "node:fs";
import AdmZip from "adm-zip";

rmSync("mta-dist", { recursive: true, force: true });
mkdirSync("mta-dist", { recursive: true });

const zip = new AdmZip();
zip.addLocalFolder("dist"); // contents of dist/ land at the zip root
zip.writeZip("mta-dist/bridgescout.zip");

console.log("wrote mta-dist/bridgescout.zip");
