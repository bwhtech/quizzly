// Renders every dicebear-kind avatar pack to static SVG, so the runtime never
// loads a dicebear library and a bought "static" pack drops in the same shape.
// Run: yarn build:avatars
import { mkdir, readFile, readdir, rm, writeFile } from "node:fs/promises";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createAvatar } from "@dicebear/core";
import * as collection from "@dicebear/collection";

const app = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const packsDir = path.join(app, "trivia_tap/avatar_packs");
const outRoot = path.join(app, "trivia_tap/public/avatars");

for (const file of await readdir(packsDir)) {
  if (!file.endsWith(".json")) continue;
  const pack = JSON.parse(await readFile(path.join(packsDir, file), "utf8"));
  if (pack.kind !== "dicebear") continue;

  const style = collection[pack.style];
  if (!style)
    throw new Error(`${pack.id}: unknown dicebear style "${pack.style}"`);

  const outDir = path.join(outRoot, pack.id);
  await rm(outDir, { recursive: true, force: true });
  await mkdir(outDir, { recursive: true });

  for (const id of pack.avatars) {
    // Framing is the pack's business: notionists draws half-body portraits,
    // which read as a cropped torso until zoomed onto the face.
    const svg = createAvatar(style, {
      seed: id,
      radius: 50,
      backgroundColor: pack.background_colors ?? [],
      ...(pack.framing ?? {}),
    }).toString();
    await writeFile(path.join(outDir, `${id}.svg`), svg);
  }
  console.log(
    `${pack.id}: ${pack.avatars.length} avatars -> ${path.relative(
      app,
      outDir
    )}`
  );
}
