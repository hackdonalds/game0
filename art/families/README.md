# Families

A family is a body plan that shares one skeleton, one base mesh and one gear kit. Its `contract.json` fixes bone names, sockets, body regions, gear layers, dye channels, slider names and per-people clamps. Everything the `asset-forge` skill makes follows it, so gear fits every body and clips play on every body.

| Family | For |
| --- | --- |
| `humanoid` | Galeborne, Anchorkin, Rootwardens, humanoid NPCs |
| `quadruped` | Four-legged creatures and mounts |
| `rigid` | Ships, buildings, environment pieces, modular kits, props |

Layout per family: `base.glb`, `peoples/<id>.body.glb` and `.rest.json`, `anims/<set>.glb`, `gear/<slot>/<id>.glb` with `.part.json` and `.dye.png`. Commands: `bun run art:forge`.
