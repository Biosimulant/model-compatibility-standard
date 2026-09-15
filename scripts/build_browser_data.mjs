import { readdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const specRoot = join(root, "spec", "v0.1");
const output = join(root, "typescript", "src", "browser-data.json");
const includedRoots = ["catalogue", "profiles", "rules", "schemas"];
const files = {};

function visit(directory) {
  for (const name of readdirSync(directory).sort()) {
    const path = join(directory, name);
    if (statSync(path).isDirectory()) {
      visit(path);
    } else if (name.endsWith(".json")) {
      files[relative(specRoot, path).split("\\").join("/")] = JSON.parse(
        readFileSync(path, "utf8"),
      );
    }
  }
}

for (const directory of includedRoots) visit(join(specRoot, directory));

writeFileSync(output, `${JSON.stringify({ files })}\n`);
